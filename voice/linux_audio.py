"""Optional Linux speech and WAV playback; no packages installed at runtime."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .tts_backends import TTSBackendResult


def play_wav(path: Path) -> TTSBackendResult:
    result = TTSBackendResult(ok=False, mode="wav_file", audio_path=str(path), metadata={"played": False})
    if not path.is_file():
        result.metadata["error"] = f"Audio file missing: {path}"
        return result
    executable = next((found for name in ("paplay", "aplay") if (found := shutil.which(name))), None)
    if not executable:
        result.metadata["error"] = "Install paplay (PulseAudio utilities) or aplay (ALSA utilities) for WAV playback."
        return result
    try:
        subprocess.run([executable, str(path.resolve())], check=True, capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
        result.metadata["error"] = str(exc)
        return result
    result.ok = True
    result.metadata.update(playback=Path(executable).name, played=True)
    return result


class EspeakBackend:
    """Basic offline replacement for SAPI, not a recreation of Microsoft voices."""

    def __init__(self, rate: int = 145, volume: float = 0.9, voice_language: str = "en-gb", **_kwargs) -> None:
        self.rate = rate
        self.volume = volume
        self.language = voice_language.split(",")[0] or "en-gb"

    def _run(self, text: str, target: Path | None = None) -> TTSBackendResult:
        result = TTSBackendResult(ok=False, text=text, mode="espeak", metadata={"played": False})
        executable = shutil.which("espeak-ng") or shutil.which("espeak")
        if not executable:
            result.metadata["error"] = "Install espeak-ng to enable Linux base speech."
            return result
        command = [executable, "-v", self.language, "-s", str(max(80, min(450, self.rate))), "-a", str(max(0, min(200, int(self.volume * 100)))), "--stdin"]
        try:
            if target is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                command.extend(["-w", str(target.resolve())])
            subprocess.run(command, input=text, text=True, capture_output=True, check=True, timeout=120)
            if target is not None and (not target.is_file() or target.stat().st_size <= 44):
                raise RuntimeError("Speech engine did not produce a nonempty WAV file")
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            result.metadata["error"] = str(exc)
            return result
        result.ok = True
        result.audio_path = str(target) if target is not None else None
        result.metadata.update(voice={"name": self.language, "language": self.language}, played=target is None, playback="espeak" if target is None else "wav_file")
        return result

    def speak(self, text: str) -> TTSBackendResult:
        return self._run(text)

    def synthesize(self, text: str) -> TTSBackendResult:
        return self.speak(text)

    def synthesize_to_wav(self, text: str, target: Path) -> TTSBackendResult:
        return self._run(text, target)
