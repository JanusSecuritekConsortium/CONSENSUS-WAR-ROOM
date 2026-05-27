from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.registry import HeaderLogoLayout, THEME_GRAPHIC_ASSETS
from ui.assets.logo_normalizer import read_normalized_logo
from ui.themes.catalog import get_gui_theme_options


def test_all_gui_themes_register_header_layout_metadata() -> None:
    for theme in get_gui_theme_options():
        layout = THEME_GRAPHIC_ASSETS[theme.key].header_layout

        assert isinstance(layout, HeaderLogoLayout)
        assert layout.logo_font_size > 0
        assert layout.logo_top_padding >= 0
        assert layout.logo_bottom_padding >= 0
        assert layout.logo_vertical_align in {"top", "center", "bottom"}
        assert layout.logo_horizontal_align in {"left", "center", "right"}
        assert isinstance(layout.logo_box_scroll_enabled, bool)


def test_tall_theme_layouts_fit_header_height_budget() -> None:
    for theme_key in ("wh40k", "helldivers", "military"):
        asset = THEME_GRAPHIC_ASSETS[theme_key]
        layout = asset.header_layout
        logo = read_normalized_logo(asset.logo_path)
        max_text_height = logo.height * layout.logo_font_size

        if max_text_height + layout.logo_top_padding + layout.logo_bottom_padding > 142:
            assert layout.logo_box_scroll_enabled is True
        else:
            assert max_text_height + layout.logo_top_padding + layout.logo_bottom_padding <= 142


if __name__ == "__main__":
    test_all_gui_themes_register_header_layout_metadata()
    test_tall_theme_layouts_fit_header_height_budget()
    print("test_theme_header_layout_metadata PASS")
