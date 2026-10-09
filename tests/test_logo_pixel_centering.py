from pathlib import Path
import pytest
from PIL import ImageFont
from ui.components.header import header_logo_layout, header_logo_text, supersampled_logo_metrics, theme_logo_layout_mode
from ui.themes.catalog import THEMES
from tests.helpers.gui_harness import build_layout_for


@pytest.mark.parametrize("key", ["eva", "nerv", "wh40k", "military", "helldivers"])
def test_center_uses_measured_consolas_advance(key):
    font_path = Path("C:/Windows/Fonts/consola.ttf")
    if not font_path.exists():
        pytest.skip("Windows Consolas measurement")
    advance = ImageFont.truetype(str(font_path), 1000).getlength("X") / 1000
    layout = header_logo_layout(THEMES[key])
    metrics = supersampled_logo_metrics(header_logo_text(THEMES[key]),
        base_font_size=int(layout.logo_font_size), cell_width=layout.logo_box_width,
        cell_height=layout.logo_box_height or 162, line_height_factor=layout.logo_line_height)
    unit = advance * layout.logo_font_size * metrics.fit_scale
    left = metrics.canvas_left + metrics.visible_min_column * unit + layout.logo_offset_x
    right = metrics.canvas_left + metrics.visible_max_column * unit + layout.logo_offset_x
    assert abs((left + right) / 2 - metrics.cell_width / 2) < 0.1
    assert left >= 5 and right <= metrics.cell_width - 5


def test_helldivers_has_bounded_viewport_instead_of_clipped_percentage_region():
    box = build_layout_for("helldivers").content.controls[0].content.controls[0]
    assert theme_logo_layout_mode(THEMES["helldivers"])["mode"] == "supersampled_rect"
    assert box.width == 380 and box.expand is None
    assert box.content.controls[0].width == box.width


@pytest.mark.parametrize("key,offset", [("eva", -4), ("nerv", -4), ("military", -1.5), ("wh40k", -1)])
def test_vertical_correction_matches_screenshot_measurements(key, offset):
    assert header_logo_layout(THEMES[key]).logo_offset_y == offset
