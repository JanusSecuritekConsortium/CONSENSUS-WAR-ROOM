from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.registry import HeaderLogoLayout, THEME_GRAPHIC_ASSETS, WarRoomLayoutMetadata
from ui.assets.logo_normalizer import read_normalized_logo
from ui.components.header import GUI_LOGO_BOX_HEIGHT, supersampled_logo_metrics, theme_logo_layout_mode
from ui.themes.catalog import THEMES, get_gui_theme_options


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
        assert isinstance(THEME_GRAPHIC_ASSETS[theme.key].layout_metadata, WarRoomLayoutMetadata)


def test_tall_theme_layouts_fit_header_height_budget() -> None:
    for theme_key in ("wh40k", "helldivers", "military"):
        asset = THEME_GRAPHIC_ASSETS[theme_key]
        layout = asset.header_layout
        if theme_logo_layout_mode(THEMES[theme_key])["mode"] in {"supersampled_square", "supersampled_rect", "supersampled_banner"}:
            logo_text = asset.logo_path.read_bytes().decode("utf-8")
            cell_width = int(layout.logo_box_width or GUI_LOGO_BOX_HEIGHT)
            cell_height = int(layout.logo_box_height or GUI_LOGO_BOX_HEIGHT)
            metrics = supersampled_logo_metrics(
                logo_text,
                base_font_size=int(layout.logo_font_size),
                cell_width=cell_width,
                cell_height=cell_height,
                line_height_factor=layout.logo_line_height,
            )
            assert metrics.fit_scale < 1.0
            assert metrics.visible_top >= 6
            assert metrics.visible_bottom <= cell_height - 6
            continue
        logo = read_normalized_logo(asset.logo_path)
        max_text_height = logo.height * layout.logo_font_size

        budget = layout.logo_box_height or GUI_LOGO_BOX_HEIGHT
        if max_text_height + layout.logo_top_padding + layout.logo_bottom_padding > budget:
            assert layout.logo_box_scroll_enabled is True
        else:
            assert max_text_height + layout.logo_top_padding + layout.logo_bottom_padding <= budget


if __name__ == "__main__":
    test_all_gui_themes_register_header_layout_metadata()
    test_tall_theme_layouts_fit_header_height_budget()
    print("test_theme_header_layout_metadata PASS")
