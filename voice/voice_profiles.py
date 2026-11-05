from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from core.paths import SYSTEM_ROOT, on_portable_drive


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
    for profile in config.get("profiles", {}).values():
        for key in PATH_KEYS:
            value = profile.get(key)
            if value:
                profile[key] = resolve_voice_path(str(value))
    return config


PATH_KEYS = ("rvc_model_path", "rvc_index_path", "rvc_workdir", "rvc_python", "native_python", "rvc_ffmpeg_dir", "output_dir")
DRIVE_PREFIX = "{drive}"


def resolve_voice_path(value: str) -> str:
    """Resolve a voice setting path so the SSD works under any drive letter.

    ``{drive}/...`` is on the portable drive CONSENSUS runs from, a relative path is inside this
    checkout, and an explicit absolute path (``C:/...``) is kept as written.
    """
    if value.startswith(DRIVE_PREFIX):
        return str(on_portable_drive(*Path(value[len(DRIVE_PREFIX):].lstrip("/\\")).parts))
    if Path(value).is_absolute() or (len(value) > 1 and value[1] == ":"):
        return value
    return str(SYSTEM_ROOT / value)


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
