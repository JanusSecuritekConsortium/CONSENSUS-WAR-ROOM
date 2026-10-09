from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from core.paths import SYSTEM_ROOT


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
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if sys.platform.startswith("linux"):
        override_path = config_path.with_name(config_path.stem + ".linux.json")
        if override_path.exists():
            overrides = json.loads(override_path.read_text(encoding="utf-8"))
            for name, settings in overrides.get("profiles", {}).items():
                config.setdefault("profiles", {}).setdefault(name, {}).update(settings)
    path_keys = {"rvc_model_path", "rvc_index_path", "rvc_workdir", "rvc_python", "native_python", "rvc_ffmpeg_dir", "output_dir"}
    for profile in config.get("profiles", {}).values():
        for key in path_keys:
            value = profile.get(key)
            if value and not Path(value).is_absolute():
                # Preserve explicit Windows paths; Linux overrides replace these.
                if len(value) > 1 and value[1] == ":":
                    continue
                profile[key] = str(SYSTEM_ROOT / value)
    return config


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
