"""Corporate C2 branding is separate from the A3 operating-system icon."""
from __future__ import annotations

import base64
from functools import lru_cache

from core.paths import RESOURCE_ROOT

BRAND_DIR = RESOURCE_ROOT / "static" / "branding"
CORPORATE_SYMBOL = BRAND_DIR / "consensus-c2-symbol-light.png"
CORPORATE_LOCKUP = BRAND_DIR / "consensus-c2-lockup-dark.svg"
DESKTOP_MASTER = BRAND_DIR / "consensus-a3-desktop.svg"


@lru_cache(maxsize=1)
def corporate_symbol_base64() -> str:
    # Embedded bytes work in source and frozen Flet sessions, independent of
    # the current directory and Flet's web asset URL handling.
    return base64.b64encode(CORPORATE_SYMBOL.read_bytes()).decode("ascii")


def validate_brand_assets() -> list[str]:
    failures = []
    for path in (CORPORATE_SYMBOL, CORPORATE_LOCKUP, DESKTOP_MASTER):
        if not path.is_file() or path.stat().st_size < 256:
            failures.append(f"Missing or empty branding asset: {path.name}")
    if CORPORATE_SYMBOL.is_file() and not CORPORATE_SYMBOL.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        failures.append("Corporate symbol is not a PNG")
    return failures
