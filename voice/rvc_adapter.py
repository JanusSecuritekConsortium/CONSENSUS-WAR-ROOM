from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Any, List, Optional

try:
    from .audio_quality import polish_wav
    from .tts_backends import TTSBackendResult, WindowsSAPIBackend
    from .text_normalization import split_speech_text
    from .voice_profiles import VoiceProfile, get_voice_profile
except ImportError:
    from voice.audio_quality import polish_wav
    from voice.tts_backends import TTSBackendResult, WindowsSAPIBackend
    from voice.text_normalization import split_speech_text
    from voice.voice_profiles import VoiceProfile, get_voice_profile


RVC_TEST_LINE = "AURELIUS route operational."


class RVCAdapter:
    """Optional local RVC voice-conversion layer for authorized voice profiles."""

    def __init__(self, profile: Optional[VoiceProfile] = None, timeout: int = 600) -> None:
        self.profile = profile or get_voice_profile("AURELIUS")
        self.timeout = timeout
        self.settings = self.profile.settings
        self.output_dir = Path(str(self.settings.get("output_dir", "G:/CONSENSUS_SYSTEM/_ARBITER/tts_audio")))
        self.model_path = Path(str(self.settings.get("rvc_model_path", "")))
        self.index_path = Path(str(self.settings.get("rvc_index_path", ""))) if self.settings.get("rvc_index_path") else None
        self.model_name = str(self.settings.get("rvc_model_name", self.model_path.name))
        self.workdir = Path(str(self.settings["rvc_workdir"])) if self.settings.get("rvc_workdir") else None
        self.python = Path(str(self.settings.get("rvc_python", sys.executable)))
        self.ffmpeg_dir = Path(str(self.settings["rvc_ffmpeg_dir"])) if self.settings.get("rvc_ffmpeg_dir") else None
        self.transpose = int(self.settings.get("transpose", 0))
        self.index_rate = float(self.settings.get("index_rate", 0.66))
        self.protect = float(self.settings.get("protect", 0.33))
        self.filter_radius = int(self.settings.get("filter_radius", 3))
        self.max_chunk_chars = int(self.settings.get("max_chunk_chars", 360))
        self.base_tts = WindowsSAPIBackend(
            rate=self.profile.rate,
            volume=self.profile.volume,
            voice_names=[str(item) for item in self.settings.get("base_voice_name", [])],
            voice_gender=str(self.settings.get("base_voice_gender", "")),
            voice_language=str(self.settings.get("base_voice_language", "")),
            strict_voice_selection=True,
        )

    def synthesize(self, text: str) -> TTSBackendResult:
        return self.speak(text)

    def speak(self, text: str) -> TTSBackendResult:
        converted = self.convert_text(text, play=True)
        if converted.ok:
            return converted
        if converted.metadata.get("playback_error"):
            print(f"RVC playback failed: {converted.metadata['playback_error']}")
        fallback = self.base_tts.speak(text)
        fallback.metadata["fallback_from"] = "rvc"
        fallback.metadata["rvc_error"] = converted.metadata.get("error", "unknown RVC error")
        if converted.audio_path:
            fallback.metadata["rvc_audio_path"] = converted.audio_path
        return fallback

    def save_only(self, text: str) -> TTSBackendResult:
        return self.convert_text(text, play=False)

    def convert_text(self, text: str, play: bool = True) -> TTSBackendResult:
        chunks = split_speech_text(text, max_chars=self.max_chunk_chars)
        if not chunks:
            return TTSBackendResult(ok=False, text=text, mode="rvc", metadata={"error": "empty_text"})
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = f"{time.strftime('%Y%m%d_%H%M%S')}_{time.time_ns() % 1_000_000:06d}"
        slug = self.profile.name.lower()
        if len(chunks) == 1:
            return self._convert_single(chunks[0], stamp=stamp, play=play)

        converted_parts: List[Path] = []
        temporary_paths: List[Path] = []
        for index, chunk in enumerate(chunks, start=1):
            part = self._convert_single(chunk, stamp=f"{stamp}_part{index:03d}", play=False)
            if not part.ok or not part.audio_path:
                part.metadata["chunk"] = index
                part.metadata["chunk_count"] = len(chunks)
                return part
            converted_path = Path(part.audio_path)
            converted_parts.append(converted_path)
            temporary_paths.extend(
                [
                    converted_path,
                    self.output_dir / f"{slug}_base_{stamp}_part{index:03d}.wav",
                ]
            )

        converted_wav = self.output_dir / f"{slug}_rvc_{stamp}.wav"
        try:
            self._concatenate_wavs(converted_parts, converted_wav)
        except Exception as exc:
            return TTSBackendResult(
                ok=False,
                text=" ".join(chunks),
                mode="rvc",
                metadata={"error": f"failed to concatenate RVC chunks: {exc}", "chunk_count": len(chunks)},
            )
        finally:
            for path in temporary_paths:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

        if not play:
            return TTSBackendResult(
                ok=True,
                text=" ".join(chunks),
                mode="rvc",
                audio_path=str(converted_wav),
                metadata={"playback": "skipped", "chunk_count": len(chunks)},
            )
        played = self._play_wav(converted_wav)
        if not played.ok:
            return TTSBackendResult(
                ok=False,
                text=" ".join(chunks),
                mode="rvc",
                audio_path=str(converted_wav),
                metadata={
                    "error": "converted WAV playback failed",
                    "playback_error": played.metadata.get("error", "converted WAV playback failed"),
                    "chunk_count": len(chunks),
                },
            )
        return TTSBackendResult(
            ok=True,
            text=" ".join(chunks),
            mode="rvc",
            audio_path=str(converted_wav),
            metadata={"playback": played.metadata.get("playback", "unknown"), "played": True, "chunk_count": len(chunks)},
        )

    def _convert_single(self, cleaned: str, *, stamp: str, play: bool) -> TTSBackendResult:
        slug = self.profile.name.lower()
        base_wav = self.output_dir / f"{slug}_base_{stamp}.wav"
        converted_wav = self.output_dir / f"{slug}_rvc_{stamp}.wav"

        base = self.base_tts.synthesize_to_wav(cleaned, base_wav)
        print("Base TTS backend: windows_sapi")
        print(f"Base TTS python: {sys.executable}")
        print(f"Base WAV path: {base_wav}")
        if base.metadata.get("voice"):
            voice = base.metadata["voice"]
            print(
                "Base SAPI voice: "
                f"{voice.get('name', 'default')} "
                f"({voice.get('language', 'unknown')}, {voice.get('gender', 'unknown')})"
            )
        if not base.ok:
            return TTSBackendResult(ok=False, text=cleaned, mode="rvc", metadata={"error": base.metadata.get("error", "base TTS failed")})
        if not self.model_path.exists():
            return TTSBackendResult(
                ok=False,
                text=cleaned,
                mode="rvc",
                audio_path=str(base_wav),
                metadata={"error": f"missing RVC model: {self.model_path}"},
            )

        command = self._build_command(base_wav, converted_wav)
        if not command:
            return TTSBackendResult(
                ok=False,
                text=cleaned,
                mode="rvc",
                audio_path=str(base_wav),
                metadata={"error": "rvc_command is not configured"},
            )
        try:
            env = self._build_env()
            self._print_diagnostics(command)
            completed = subprocess.run(
                command,
                cwd=str(self.workdir) if self.workdir else None,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except Exception as exc:
            return TTSBackendResult(ok=False, text=cleaned, mode="rvc", audio_path=str(base_wav), metadata={"error": str(exc)})
        if completed.returncode != 0 or not converted_wav.exists():
            error = (completed.stderr or completed.stdout or "RVC conversion failed").strip()
            return TTSBackendResult(ok=False, text=cleaned, mode="rvc", audio_path=str(base_wav), metadata={"error": error[-1000:]})
        try:
            quality = polish_wav(converted_wav).as_dict()
        except Exception as exc:
            return TTSBackendResult(
                ok=False,
                text=cleaned,
                mode="rvc",
                audio_path=str(converted_wav),
                metadata={"error": f"RVC WAV post-processing failed: {exc}"},
            )
        if not play:
            return TTSBackendResult(
                ok=True,
                text=cleaned,
                mode="rvc",
                audio_path=str(converted_wav),
                metadata={"playback": "skipped", "quality": quality},
            )

        played = self._play_wav(converted_wav)
        if not played.ok:
            return TTSBackendResult(
                ok=False,
                text=cleaned,
                mode="rvc",
                audio_path=str(converted_wav),
                metadata={
                    "error": "converted WAV playback failed",
                    "playback_error": played.metadata.get("error", "converted WAV playback failed"),
                },
            )
        return TTSBackendResult(
            ok=True,
            text=cleaned,
            mode="rvc",
            audio_path=str(converted_wav),
            metadata={
                "playback": played.metadata.get("playback", "unknown"),
                "played": played.metadata.get("played", False),
                "quality": quality,
            },
        )

    @staticmethod
    def _concatenate_wavs(parts: List[Path], target: Path) -> None:
        if not parts:
            raise ValueError("no WAV parts supplied")
        parameters = None
        frames: List[bytes] = []
        for path in parts:
            with wave.open(str(path), "rb") as source:
                current = (source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getcomptype())
                if parameters is None:
                    parameters = current
                elif current != parameters:
                    raise ValueError(f"incompatible WAV parameters in {path.name}")
                frames.append(source.readframes(source.getnframes()))
        assert parameters is not None
        with wave.open(str(target), "wb") as output:
            output.setnchannels(parameters[0])
            output.setsampwidth(parameters[1])
            output.setframerate(parameters[2])
            output.writeframes(b"".join(frames))

    def _build_command(self, input_wav: Path, output_wav: Path) -> List[str]:
        raw: Any = self.settings.get("rvc_command", [])
        if isinstance(raw, str):
            parts = shlex.split(raw)
        elif isinstance(raw, list):
            parts = [str(part) for part in raw]
        else:
            parts = []
        if not parts:
            return []
        replacements = {
            "input": str(input_wav),
            "output": str(output_wav),
            "model": str(self.model_path),
            "model_name": self.model_name,
            "index": str(self.index_path or ""),
            "transpose": str(self.transpose),
            "index_rate": str(self.index_rate),
            "protect": str(self.protect),
            "filter_radius": str(self.filter_radius),
            "python": str(self.python),
        }
        return [part.format(**replacements) for part in parts]

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        extra_env = self.settings.get("rvc_env", {})
        if isinstance(extra_env, dict):
            env.update({str(key): str(value) for key, value in extra_env.items()})
        if self.ffmpeg_dir is not None:
            env["PATH"] = f"{self.ffmpeg_dir}{os.pathsep}{env.get('PATH', '')}"
        return env

    def _print_diagnostics(self, command: List[str]) -> None:
        print(f"RVC python: {self.python}")
        print(f"RVC workdir: {self.workdir}")
        print(f"RVC model: {self.model_path}")
        print(f"RVC index: {self.index_path}")
        print(f"RVC command: {' '.join(command)}")

    def _play_wav(self, path: Path) -> TTSBackendResult:
        if os.name != "nt":
            return TTSBackendResult(ok=True, text="", mode="wav_file", audio_path=str(path), metadata={"playback": "not_supported", "played": False})
        try:
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME)
        except Exception as exc:
            return TTSBackendResult(ok=False, text="", mode="wav_file", audio_path=str(path), metadata={"error": str(exc)})
        return TTSBackendResult(ok=True, text="", mode="wav_file", audio_path=str(path), metadata={"playback": "winsound", "played": True})
