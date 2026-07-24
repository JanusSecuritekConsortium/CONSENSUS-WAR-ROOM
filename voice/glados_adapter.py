from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

try:
    from ..core.paths import SYSTEM_ROOT
except ImportError:
    from core.paths import SYSTEM_ROOT

try:
    from .glados_native import default_native_project_dir, native_glados_error
    from .rvc_adapter import RVCAdapter
    from .text_normalization import normalize_for_speech
    from .tts_backends import TTSBackendResult, WindowsSAPIBackend
    from .voice_profiles import VoiceProfile, get_voice_profile
except ImportError:
    from voice.glados_native import default_native_project_dir, native_glados_error
    from voice.rvc_adapter import RVCAdapter
    from voice.text_normalization import normalize_for_speech
    from voice.tts_backends import TTSBackendResult, WindowsSAPIBackend
    from voice.voice_profiles import VoiceProfile, get_voice_profile


class GladosAdapter:
    """Adapter for the bundled open-source GLaDOS TTS project, with configured fallback."""

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        profile: Optional[VoiceProfile] = None,
        backend: Optional[str] = None,
        native_python: Optional[Path] = None,
        timeout: int = 180,
    ) -> None:
        self.profile = profile or get_voice_profile("ARBITER_GLADOS")
        self.project_dir = project_dir or self._default_project_dir()
        self.output_dir = output_dir or SYSTEM_ROOT / "_ARBITER" / "voice_tmp"
        self.timeout = timeout
        configured_backend = backend or os.getenv("ARBITER_GLADOS_BACKEND") or self.profile.backend
        self.backend = configured_backend.strip().lower()
        if self.backend == "native":
            self.backend = "glados_tts"
        if self.backend not in {"rvc", "glados_tts"}:
            raise ValueError(f"Unsupported GLaDOS backend: {configured_backend}")
        self.native_python = native_python or Path(str(self.profile.settings.get("native_python", sys.executable)))
        self.rvc = RVCAdapter(profile=self.profile, timeout=timeout) if self.backend == "rvc" else None
        self.rvc_fallback = (
            RVCAdapter(profile=self.profile, timeout=timeout)
            if self.backend == "glados_tts" and self.profile.fallback == "rvc"
            else None
        )
        self.sapi_fallback = WindowsSAPIBackend(
            rate=self.profile.rate,
            volume=self.profile.volume,
            voice_names=[str(item) for item in self.profile.settings.get("base_voice_name", [])],
            voice_gender=str(self.profile.settings.get("base_voice_gender", "")),
            voice_language=str(self.profile.settings.get("base_voice_language", "")),
            strict_voice_selection=True,
        )

    def synthesize(self, text: str) -> TTSBackendResult:
        cleaned = normalize_for_speech(text)
        if not cleaned:
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": "empty_text"})
        if self.rvc is not None:
            return self.rvc.speak(cleaned)
        local = self._synthesize_with_local_project(cleaned, play=True)
        if local.ok:
            return local
        if self.rvc_fallback is not None:
            fallback = self.rvc_fallback.speak(cleaned)
            fallback.metadata["fallback_from"] = "glados_tts"
            fallback.metadata["glados_error"] = local.metadata.get("error", "unknown GLaDOS error")
            return fallback
        fallback = self.sapi_fallback.speak(cleaned)
        fallback.metadata["fallback_from"] = "glados_tts"
        fallback.metadata["glados_error"] = local.metadata.get("error", "unknown GLaDOS error")
        return fallback

    def speak(self, text: str) -> TTSBackendResult:
        return self.synthesize(text)

    def save_only(self, text: str) -> TTSBackendResult:
        cleaned = normalize_for_speech(text)
        if not cleaned:
            return TTSBackendResult(ok=False, text=text, mode=self.backend, metadata={"error": "empty_text"})
        if self.rvc is not None:
            return self.rvc.save_only(cleaned)
        return self._synthesize_with_local_project(cleaned, play=False)

    def _synthesize_with_local_project(self, text: str, *, play: bool) -> TTSBackendResult:
        if not self.project_dir.exists():
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": f"missing project dir: {self.project_dir}"})
        engine_path = self.project_dir / "engine.py"
        if not engine_path.exists():
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": f"missing engine.py: {engine_path}"})
        asset_error = native_glados_error(self.project_dir, verify_hashes=True)
        if asset_error:
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": asset_error})
        if not self.native_python.exists():
            return TTSBackendResult(
                ok=False,
                text=text,
                mode="glados_tts",
                metadata={"error": f"missing native GLaDOS Python: {self.native_python}"},
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        key = f"{time.strftime('%Y%m%d_%H%M%S')}_{time.time_ns() % 1_000_000:06d}"
        target = self.output_dir / f"glados_tts_{key}.wav"
        script = (
            "import pathlib, shutil, sys; "
            "text = sys.argv[1]; target = pathlib.Path(sys.argv[2]); key = sys.argv[3]; "
            "pathlib.Path('audio').mkdir(exist_ok=True); "
            "import engine; "
            "ok = engine.glados_tts(text, key=key); "
            "source = pathlib.Path('audio') / f'GLaDOS-tts-temp-output-{key}.wav'; "
            "target.parent.mkdir(parents=True, exist_ok=True); "
            "shutil.copyfile(source, target); "
            "sys.exit(0 if ok and target.exists() else 1)"
        )
        try:
            completed = subprocess.run(
                [str(self.native_python), "-c", script, text, str(target), key],
                cwd=str(self.project_dir),
                env=self._native_env(),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except Exception as exc:
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": str(exc)})
        if completed.returncode != 0 or not target.exists():
            error = (completed.stderr or completed.stdout or "GLaDOS synthesis failed").strip()
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": error[-1000:]})

        if not play:
            return TTSBackendResult(
                ok=True,
                text=text,
                mode="glados_tts",
                audio_path=str(target),
                metadata={"playback": "skipped", "played": False},
            )
        played = self._play_wav(target)
        if not played.ok:
            return TTSBackendResult(
                ok=False,
                text=text,
                mode="glados_tts",
                audio_path=str(target),
                metadata={"error": played.metadata.get("error", "playback failed")},
            )
        return TTSBackendResult(
            ok=True,
            text=text,
            mode="glados_tts",
            audio_path=str(target),
            metadata={"playback": played.metadata.get("playback", "unknown"), "played": played.metadata.get("played", False)},
        )

    def _play_wav(self, path: Path) -> TTSBackendResult:
        if os.name != "nt":
            return TTSBackendResult(ok=True, text="", mode="wav_file", audio_path=str(path), metadata={"playback": "not_supported", "played": False})
        try:
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME)
        except Exception as exc:
            return TTSBackendResult(ok=False, text="", mode="wav_file", audio_path=str(path), metadata={"error": str(exc)})
        return TTSBackendResult(ok=True, text="", mode="wav_file", audio_path=str(path), metadata={"playback": "winsound", "played": True})

    @staticmethod
    def _native_env() -> dict[str, str]:
        env = os.environ.copy()
        # The verified upstream phonemizer checkpoint contains its preprocessing
        # object, so PyTorch 2.6+ must use the legacy trusted-checkpoint loader.
        env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
        return env

    @staticmethod
    def _default_project_dir() -> Path:
        return default_native_project_dir()
