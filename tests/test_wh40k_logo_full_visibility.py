from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.components.header import GUI_LOGO_BOX_HEIGHT, header_logo_layout, logo_text_control_from_box, supersampled_logo_metrics
from ui.themes.catalog import THEMES


def test_wh40k_logo_fits_header_without_scroll() -> None:
    asset = THEME_GRAPHIC_ASSETS["wh40k"]
    logo = asset.logo_path.read_bytes().decode("utf-8")
    layout = header_logo_layout(THEMES["wh40k"])
    cell_width = int(layout.logo_box_width or GUI_LOGO_BOX_HEIGHT)
    cell_height = int(layout.logo_box_height or GUI_LOGO_BOX_HEIGHT)
    metrics = supersampled_logo_metrics(
        logo,
        base_font_size=int(layout.logo_font_size),
        cell_width=cell_width,
        cell_height=cell_height,
        line_height_factor=layout.logo_line_height,
    )

    assert metrics.base_font_size == 10
    assert metrics.fit_scale < 1.0
    assert metrics.visible_left >= 6
    assert metrics.visible_right <= cell_width - 6
    assert metrics.visible_top >= 6
    assert metrics.visible_bottom <= cell_height - 6
    assert layout.logo_box_scroll_enabled is False


def test_wh40k_rendered_logo_box_contains_full_asset() -> None:
    page = build_layout_for("wh40k")
    logo_box = page.content.controls[0].content.controls[0]
    logo_text = logo_text_control_from_box(logo_box).value

    assert logo_text == THEME_GRAPHIC_ASSETS["wh40k"].logo_path.read_bytes().decode("utf-8")
    assert "@@@@@@@@" in logo_text
    assert "@@@@@@#" in logo_text
    assert logo_box.content.scroll is None


if __name__ == "__main__":
    test_wh40k_logo_fits_header_without_scroll()
    test_wh40k_rendered_logo_box_contains_full_asset()
    print("test_wh40k_logo_full_visibility PASS")
