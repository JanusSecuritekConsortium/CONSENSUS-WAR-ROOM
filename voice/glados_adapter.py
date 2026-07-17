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
    from .rvc_adapter import RVCAdapter
    from .tts_backends import TTSBackendResult, WindowsSAPIBackend
    from .voice_profiles import VoiceProfile, get_voice_profile
except ImportError:
    from voice.rvc_adapter import RVCAdapter
    from voice.tts_backends import TTSBackendResult, WindowsSAPIBackend
    from voice.voice_profiles import VoiceProfile, get_voice_profile


class GladosAdapter:
    """Adapter for the bundled open-source GLaDOS TTS project, with configured fallback."""

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        profile: Optional[VoiceProfile] = None,
        timeout: int = 180,
    ) -> None:
        self.profile = profile or get_voice_profile("ARBITER_GLADOS")
        self.project_dir = project_dir or self._default_project_dir()
        self.output_dir = output_dir or SYSTEM_ROOT / "_ARBITER" / "voice_tmp"
        self.timeout = timeout
        self.rvc = RVCAdapter(profile=self.profile, timeout=timeout) if self.profile.backend == "rvc" else None
        self.fallback = WindowsSAPIBackend(rate=self.profile.rate, volume=self.profile.volume)

    def synthesize(self, text: str) -> TTSBackendResult:
        cleaned = text.strip()
        if not cleaned:
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": "empty_text"})
        if self.rvc is not None:
            return self.rvc.speak(cleaned)
        local = self._synthesize_with_local_project(cleaned)
        if local.ok:
            return local
        fallback = self.fallback.speak(cleaned)
        fallback.metadata["fallback_from"] = "glados_tts"
        fallback.metadata["glados_error"] = local.metadata.get("error", "unknown GLaDOS error")
        return fallback

    def speak(self, text: str) -> TTSBackendResult:
        return self.synthesize(text)

    def _synthesize_with_local_project(self, text: str) -> TTSBackendResult:
        if not self.project_dir.exists():
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": f"missing project dir: {self.project_dir}"})
        engine_path = self.project_dir / "engine.py"
        if not engine_path.exists():
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": f"missing engine.py: {engine_path}"})

        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / "glados_tts.wav"
        key = str(time.time()).replace(".", "")
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
                [sys.executable, "-c", script, text, str(target), key],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except Exception as exc:
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": str(exc)})
        if completed.returncode != 0 or not target.exists():
            error = (completed.stderr or completed.stdout or "GLaDOS synthesis failed").strip()
            return TTSBackendResult(ok=False, text=text, mode="glados_tts", metadata={"error": error[-1000:]})

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
    def _default_project_dir() -> Path:
        preferred = SYSTEM_ROOT / "external" / "glados-tts" / "glados-tts-main"
        if preferred.exists():
            return preferred
        return SYSTEM_ROOT / "_ARBITER" / "Bot" / "Voice" / "glados-tts-main"
