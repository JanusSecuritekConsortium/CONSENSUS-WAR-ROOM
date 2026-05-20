from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


CONFIG_PATH = Path(__file__).with_name("voice_config.json")


@dataclass(frozen=True)
class VoiceProfile:
    name: str
    backend: str
    voice: str
    fallback: str
    rate: int
    volume: float
    settings: Dict[str, Any]


def load_voice_config(path: Optional[Path] = None) -> Dict[str, Any]:
    config_path = path or CONFIG_PATH
    return json.loads(config_path.read_text(encoding="utf-8"))


def get_voice_profile(name: str, path: Optional[Path] = None) -> VoiceProfile:
    config = load_voice_config(path)
    profiles = config.get("profiles", {})
    if name not in profiles:
        raise KeyError(f"Unknown voice profile: {name}")
    raw = profiles[name]
    return VoiceProfile(
        name=name,
        backend=str(raw.get("backend", config.get("default_backend", "windows_sapi"))),
        voice=str(raw.get("voice", name.lower())),
        fallback=str(raw.get("fallback", config.get("default_backend", "windows_sapi"))),
        rate=int(raw.get("rate", 145)),
        volume=float(raw.get("volume", 0.9)),
        settings={key: value for key, value in raw.items() if key not in {"backend", "voice", "fallback", "rate", "volume"}},
    )
