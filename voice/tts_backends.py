from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TTSBackendResult:
    ok: bool
    text: str = ""
    mode: str = "unknown"
    audio_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def list_sapi_voices() -> List[Dict[str, str]]:
    if os.name != "nt":
        return []
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$speaker.GetInstalledVoices() | ForEach-Object { "
        "$v=$_.VoiceInfo; "
        "Write-Output ($v.Name + '|' + $v.Culture.Name + '|' + $v.Gender + '|' + $v.Age) "
        "}; "
        "$speaker.Dispose()"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=30,
    )
    voices: List[Dict[str, str]] = []
    if completed.returncode != 0:
        return voices
    for line in completed.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 4:
            voices.append({"name": parts[0], "language": parts[1], "gender": parts[2], "age": parts[3]})
    return voices


class WindowsSAPIBackend:
    def __init__(
        self,
        rate: int = 145,
        volume: float = 0.9,
        voice_names: Optional[List[str]] = None,
        voice_gender: str = "",
        voice_language: str = "",
    ) -> None:
        self.rate = rate
        self.volume = volume
        self.voice_names = voice_names or []
        self.voice_gender = voice_gender
        self.voice_language = voice_language
        self._selected_voice: Optional[Dict[str, str]] = None

    def speak(self, text: str) -> TTSBackendResult:
        if os.name != "nt":
            return TTSBackendResult(ok=False, text=text, mode="windows_sapi", metadata={"error": "Windows SAPI unavailable"})
        escaped = text.replace("'", "''")
        selected = self.select_voice(print_diagnostics=True)
        escaped_voice = selected.get("name", "").replace("'", "''") if selected else ""
        volume = max(0, min(100, int(self.volume * 100)))
        rate = max(-10, min(10, int((self.rate - 145) / 10)))
        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"if ('{escaped_voice}') {{ $speaker.SelectVoice('{escaped_voice}'); }} "
            f"$speaker.Volume = {volume}; "
            f"$speaker.Rate = {rate}; "
            f"$speaker.Speak('{escaped}'); "
            "$speaker.Dispose()"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout or "Windows SAPI playback failed").strip()
            return TTSBackendResult(ok=False, text=text, mode="windows_sapi", metadata={"error": error})
        return TTSBackendResult(
            ok=True,
            text=text,
            mode="windows_sapi",
            metadata={"voice": selected, "playback": "windows_sapi", "played": True},
        )

    def synthesize(self, text: str) -> TTSBackendResult:
        return self.speak(text)

    def synthesize_to_wav(self, text: str, target: Path) -> TTSBackendResult:
        if os.name != "nt":
            return TTSBackendResult(ok=False, text=text, mode="windows_sapi", metadata={"error": "Windows SAPI unavailable"})
        target.parent.mkdir(parents=True, exist_ok=True)
        escaped_text = text.replace("'", "''")
        escaped_path = str(target).replace("'", "''")
        selected = self.select_voice(print_diagnostics=True)
        escaped_voice = selected.get("name", "").replace("'", "''") if selected else ""
        volume = max(0, min(100, int(self.volume * 100)))
        rate = max(-10, min(10, int((self.rate - 145) / 10)))
        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"if ('{escaped_voice}') {{ $speaker.SelectVoice('{escaped_voice}'); }} "
            f"$speaker.Volume = {volume}; "
            f"$speaker.Rate = {rate}; "
            f"$speaker.SetOutputToWaveFile('{escaped_path}'); "
            f"$speaker.Speak('{escaped_text}'); "
            "$speaker.Dispose()"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0 or not target.exists():
            error = (completed.stderr or completed.stdout or "Windows SAPI WAV synthesis failed").strip()
            return TTSBackendResult(ok=False, text=text, mode="windows_sapi", metadata={"error": error})
        return TTSBackendResult(ok=True, text=text, mode="windows_sapi", audio_path=str(target), metadata={"voice": selected})

    def select_voice(self, print_diagnostics: bool = False) -> Dict[str, str]:
        if self._selected_voice is not None:
            return self._selected_voice
        voices = list_sapi_voices()
        if not voices:
            self._selected_voice = {}
            if print_diagnostics:
                print("Windows SAPI selected voice: default (no installed voices enumerated)")
            return self._selected_voice

        selected = self._best_voice(voices)
        exact_requested = bool(self.voice_names) and any(
            requested.lower() in selected.get("name", "").lower()
            for requested in self.voice_names
        )
        if self.voice_names and not exact_requested:
            print("Requested Windows SAPI voice not found. Available voices:")
            print(format_sapi_voices(voices))
        self._selected_voice = selected
        if print_diagnostics:
            print(
                "Windows SAPI selected voice: "
                f"{selected.get('name', 'default')} "
                f"({selected.get('language', 'unknown')}, {selected.get('gender', 'unknown')})"
            )
        return selected

    def _best_voice(self, voices: List[Dict[str, str]]) -> Dict[str, str]:
        preferred_names = [name.lower() for name in self.voice_names]
        preferred_gender = self.voice_gender.lower()
        preferred_languages = [
            item.strip().lower()
            for item in self.voice_language.replace(";", ",").split(",")
            if item.strip()
        ]

        def score(voice: Dict[str, str]) -> tuple[int, str]:
            name = voice.get("name", "").lower()
            language = voice.get("language", "").lower()
            gender = voice.get("gender", "").lower()
            value = 0
            for rank, requested in enumerate(preferred_names):
                if requested and requested in name:
                    value += 1000 - rank
            if preferred_gender and preferred_gender == gender:
                value += 100
            if any(language == preferred for preferred in preferred_languages):
                value += 80
            elif any(language.startswith(preferred.split("-")[0]) for preferred in preferred_languages):
                value += 40
            if language.startswith("en-"):
                value += 20
            return value, voice.get("name", "")

        return max(voices, key=score)


def format_sapi_voices(voices: Optional[List[Dict[str, str]]] = None) -> str:
    items = voices if voices is not None else list_sapi_voices()
    if not items:
        return "No Windows SAPI voices found."
    return "\n".join(
        f"- {voice.get('name', '--')} | {voice.get('language', '--')} | {voice.get('gender', '--')} | {voice.get('age', '--')}"
        for voice in items
    )
