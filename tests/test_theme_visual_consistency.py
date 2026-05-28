from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.themes.catalog import get_gui_theme_options


def test_all_gui_themes_use_ascii_registry_assets_and_center_metadata() -> None:
    for theme in get_gui_theme_options():
        asset = THEME_GRAPHIC_ASSETS[theme.key]
        layout = asset.header_layout

        assert asset.logo_path.suffix == ".txt"
        assert layout.logo_horizontal_align == "center"
        assert layout.logo_vertical_align == "center"
        assert layout.logo_font_size > 0


if __name__ == "__main__":
    test_all_gui_themes_use_ascii_registry_assets_and_center_metadata()
    print("test_theme_visual_consistency PASS")
