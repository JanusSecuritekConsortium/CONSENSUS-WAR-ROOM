from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_theme_ascii_assets_meet_registered_dimensions() -> None:
    for theme_key, asset in THEME_GRAPHIC_ASSETS.items():
        logo = read_normalized_logo(asset.logo_path)

        assert asset.expected_min_lines <= logo.height <= asset.expected_max_lines, theme_key
        assert asset.expected_min_width <= logo.width <= asset.max_width, theme_key


def test_military_gui_logo_preserves_supplied_glyph_artwork() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["military"].logo_path)

    assert (logo.height, logo.width) == (66, 100)
    assert logo.lines[0] == logo.lines[-1] == "                                               ------"
    assert "---×÷÷×----" in logo.text


if __name__ == "__main__":
    test_theme_ascii_assets_meet_registered_dimensions()
    test_military_gui_logo_preserves_supplied_glyph_artwork()
    print("test_theme_ascii_dimensions PASS")
