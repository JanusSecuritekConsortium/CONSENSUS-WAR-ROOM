from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.components.header import compact_logo_text
from ui.themes.catalog import THEMES


USER_HELLDIVERS_SHA256 = "0AF754842CC538EBE8B66E8690EFA2547E949CAF506CC48739F3563703BBD430"
FORBIDDEN_HELLDIVERS_TOKENS = (
    "O O",
    "LIBERTY WINGS",
    "MANAGED DEMOCRACY ONLINE",
    "SUPER EARTH COMMAND",
)


def test_helldivers_header_asset_matches_user_framebuffer_hash() -> None:
    raw = THEME_GRAPHIC_ASSETS["helldivers"].logo_path.read_bytes()

    assert hashlib.sha256(raw).hexdigest().upper() == USER_HELLDIVERS_SHA256


def test_helldivers_header_uses_asset_without_generated_captions() -> None:
    text = compact_logo_text(THEMES["helldivers"])

    assert text == THEME_GRAPHIC_ASSETS["helldivers"].logo_path.read_bytes().decode("utf-8")
    assert "####     ########    ####" in text
    for token in FORBIDDEN_HELLDIVERS_TOKENS:
        assert token not in text


if __name__ == "__main__":
    test_helldivers_header_asset_matches_user_framebuffer_hash()
    test_helldivers_header_uses_asset_without_generated_captions()
    print("test_helldivers_uses_user_ascii_asset PASS")
