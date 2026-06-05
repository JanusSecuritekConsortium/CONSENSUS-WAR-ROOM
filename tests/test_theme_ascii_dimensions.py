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


def test_military_gui_logo_preserves_excomm_wordmark_and_title_spacing() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["military"].logo_path)
    title_index = logo.lines.index("                        CONSENSUS WAR ROOM")

    assert "███████╗██╗  ██╗" in logo.text
    assert logo.lines[title_index - 1] == ""


if __name__ == "__main__":
    test_theme_ascii_assets_meet_registered_dimensions()
    test_military_gui_logo_preserves_excomm_wordmark_and_title_spacing()
    print("test_theme_ascii_dimensions PASS")
