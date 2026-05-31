from __future__ import annotations

from pathlib import Path
from typing import Any

from core.paths import RESOURCE_ROOT


APP_ICON_DIR = RESOURCE_ROOT / "static" / "icons"
APP_ICON_PNG = APP_ICON_DIR / "consensus_icon.png"
APP_ICON_PNG_256 = APP_ICON_DIR / "consensus_icon_256.png"
APP_ICON_ICO = APP_ICON_DIR / "consensus_icon.ico"
APP_ICON_SUPPORTED_EXTENSIONS = {".ico", ".png"}
APP_ICON_MIN_BYTES = 256


def resolve_app_icon_path(prefer_ico: bool = True) -> Path | None:
    candidates = (APP_ICON_ICO, APP_ICON_PNG_256, APP_ICON_PNG) if prefer_ico else (APP_ICON_PNG_256, APP_ICON_PNG, APP_ICON_ICO)
    for path in candidates:
        if path.exists() and path.is_file() and path.stat().st_size >= APP_ICON_MIN_BYTES:
            return path
    return None


def validate_app_icon_assets() -> dict[str, Any]:
    assets: dict[str, dict[str, Any]] = {}
    for path in (APP_ICON_ICO, APP_ICON_PNG, APP_ICON_PNG_256):
        exists = path.exists() and path.is_file()
        suffix_ok = path.suffix.lower() in APP_ICON_SUPPORTED_EXTENSIONS
        size = path.stat().st_size if exists else 0
        readable = False
        if exists:
            try:
                with path.open("rb") as handle:
                    header = handle.read(16)
                readable = bool(header)
            except OSError:
                readable = False
        assets[path.name] = {
            "path": str(path),
            "exists": exists,
            "extension_ok": suffix_ok,
            "non_empty": size >= APP_ICON_MIN_BYTES,
            "readable": readable,
            "size_bytes": size,
        }
    configured = resolve_app_icon_path()
    return {
        "status": "READY" if configured else "MISSING",
        "configured_icon": str(configured) if configured else None,
        "assets": assets,
        "not_old_default": configured is not None and configured.name.startswith("consensus_icon"),
    }


def apply_app_icon_to_page(page: Any) -> Path | None:
    icon_path = resolve_app_icon_path()
    if icon_path is None:
        return None
    window = getattr(page, "window", None)
    if window is not None and hasattr(window, "icon"):
        window.icon = str(icon_path)
    elif hasattr(page, "window_icon"):
        setattr(page, "window_icon", str(icon_path))
    return icon_path
