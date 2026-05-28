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


USER_EVA_SHA256 = "5C10F1A59339B6A788880C4187481C0D3290ABDDC1DFF9DA80389FA8684DF476"
FORBIDDEN_EVA_TOKENS = ("NERV GEOMETRIC MAGI MARK", "CASPER", "BALTHASAR", "MELCHIOR")


def test_eva_header_asset_matches_user_framebuffer_hash() -> None:
    raw = THEME_GRAPHIC_ASSETS["eva"].logo_path.read_bytes()

    assert hashlib.sha256(raw).hexdigest().upper() == USER_EVA_SHA256


def test_eva_header_uses_asset_without_generated_captions() -> None:
    text = compact_logo_text(THEMES["eva"])

    assert text == THEME_GRAPHIC_ASSETS["eva"].logo_path.read_bytes().decode("utf-8")
    assert "###########################" in text
    for token in FORBIDDEN_EVA_TOKENS:
        assert token not in text


if __name__ == "__main__":
    test_eva_header_asset_matches_user_framebuffer_hash()
    test_eva_header_uses_asset_without_generated_captions()
    print("test_eva_uses_user_ascii_asset PASS")
