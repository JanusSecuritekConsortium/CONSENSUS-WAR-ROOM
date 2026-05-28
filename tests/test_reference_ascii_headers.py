from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_eva_header_is_nerv_reference_derived_ascii() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["eva"].logo_path)

    assert "###########################" in logo.text
    assert "NERV GEOMETRIC MAGI MARK" not in logo.text
    assert "CASPER" not in logo.text
    assert logo.width <= 88
    assert logo.height == 56


def test_helldivers_header_is_skull_wings_reference_ascii() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["helldivers"].logo_path)

    assert "####     ########    ####" in logo.text
    assert "O O" not in logo.text
    assert "MANAGED DEMOCRACY ONLINE" not in logo.text
    assert logo.width <= 88


def test_wh40k_header_box_is_tighter_than_previous_wide_box() -> None:
    layout = THEME_GRAPHIC_ASSETS["wh40k"].header_layout

    assert layout.logo_box_width is not None
    assert layout.logo_box_width <= 450
    assert layout.logo_box_scroll_enabled is False


if __name__ == "__main__":
    test_eva_header_is_nerv_reference_derived_ascii()
    test_helldivers_header_is_skull_wings_reference_ascii()
    test_wh40k_header_box_is_tighter_than_previous_wide_box()
    print("test_reference_ascii_headers PASS")
