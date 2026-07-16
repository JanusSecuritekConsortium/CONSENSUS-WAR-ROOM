from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.components.header import (
    GUI_LOGO_BOX_HEIGHT,
    header_logo_layout,
    logo_runtime_diagnostics,
    logo_text_control_from_box,
    supersampled_logo_metrics,
)
from ui.components.telemetry_widgets import (
    EVA_MAGI_METER_HEIGHT,
    build_eva_telemetry,
    estimate_eva_telemetry_content_height,
)
from ui.layout_contract import CENTER_COLUMN_FLEX, FOOTER_HEIGHT, LEFT_COLUMN_FLEX, PROPOSAL_HEIGHT, RIGHT_COLUMN_FLEX
from ui.themes.catalog import THEMES


SUPPORTED_VIEWPORTS = ((1536, 864), (1920, 1080), (2560, 1440))


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def test_eva_telemetry_compacts_inside_header_without_vertical_thermal_gauges() -> None:
    metrics = {
        "cpu": {"percent": 18.6},
        "ram": {"percent": 78.4},
        "disk": {"percent": 78.0},
        "gpu": {"usage_percent": 1.8, "vram_percent": 39.0},
        "gpu_core_temp_c": 39.0,
        "thermal": {"gpu_core_temp_c": 39.0, "thermal_state": "NORMAL"},
    }
    control = build_eva_telemetry("eva", metrics, {}, THEMES["eva"], available_width=360)
    roles = [getattr(child, "data", {}).get("role") for child in _walk(control) if isinstance(getattr(child, "data", None), dict)]
    text = "\n".join(str(child.value) for child in _walk(control) if hasattr(child, "value"))

    assert control.data["telemetry_layout_id"] == "eva_magi_columns_v2"
    assert control.data["magi_meter_height"] == EVA_MAGI_METER_HEIGHT
    assert EVA_MAGI_METER_HEIGHT <= 34
    assert roles.count("magi_vertical_channel") == 3
    assert "thermal_vertical_meter" not in roles
    assert "at_thermal_compact_row" in roles
    assert "CORE N/A" in text
    assert "PATTERN 39 C" in text
    assert "THERMAL NORMAL" in text

    for _width, _height in SUPPORTED_VIEWPORTS:
        header_inner_height = GUI_LOGO_BOX_HEIGHT
        assert control.data["estimated_content_height"] == estimate_eva_telemetry_content_height(compact=False)
        assert control.data["estimated_content_height"] <= header_inner_height - 14
        assert 6 <= (header_inner_height - control.data["estimated_content_height"]) / 2


def test_wh40k_supersampled_visible_glyph_bounds_apply_optical_offset() -> None:
    logo = THEME_GRAPHIC_ASSETS["wh40k"].logo_path.read_bytes().decode("utf-8")
    layout = header_logo_layout(THEMES["wh40k"])
    metrics = supersampled_logo_metrics(
        logo,
        base_font_size=int(layout.logo_font_size),
        cell_width=int(layout.logo_box_width or GUI_LOGO_BOX_HEIGHT),
        cell_height=int(layout.logo_box_height or GUI_LOGO_BOX_HEIGHT),
        line_height_factor=layout.logo_line_height,
    )
    diagnostic = logo_runtime_diagnostics("wh40k", header_width=1920)
    left, right, top, bottom = diagnostic["clearances"]
    raw_canvas_center_left = (metrics.cell_width - (metrics.natural_width * metrics.fit_scale)) / 2

    assert diagnostic["optical_offset_x"] == 6
    assert left > right
    assert round(left - right, 3) == 12.0
    assert abs(top - bottom) <= 1.0
    assert min(left, right, top, bottom) >= 5
    assert abs(metrics.canvas_left - raw_canvas_center_left) > 1.0


def test_military_logo_region_and_artwork_match_final_geometry() -> None:
    diagnostic = logo_runtime_diagnostics("military", header_width=1920)
    left, right, _top, _bottom = diagnostic["clearances"]
    logo_box = build_layout_for("military").content.controls[0].content.controls[0]
    logo_text = logo_text_control_from_box(logo_box)

    assert diagnostic["renderer_mode"] == "supersampled_banner"
    assert 395 <= diagnostic["logo_region_width"] <= 405
    assert 110 <= diagnostic["visible_artwork_width"] <= 120
    assert 118 <= diagnostic["visible_artwork_height"] <= 126
    assert abs(left - right) <= 1
    assert left >= 140
    assert right >= 140
    assert logo_box.width == 400
    assert logo_box.content.scroll is None
    assert logo_text.value == THEME_GRAPHIC_ASSETS["military"].logo_path.read_bytes().decode("utf-8")


def test_frozen_body_proposal_and_footer_contract_remains_unchanged() -> None:
    layout = build_layout_for("eva")
    body = layout.content.controls[1].content
    proposal_region = body.controls[1].content.controls[0]
    footer = layout.content.controls[2]

    assert tuple(control.expand for control in body.controls) == (LEFT_COLUMN_FLEX, CENTER_COLUMN_FLEX, RIGHT_COLUMN_FLEX)
    assert proposal_region.height == PROPOSAL_HEIGHT
    assert footer.height == FOOTER_HEIGHT


if __name__ == "__main__":
    test_eva_telemetry_compacts_inside_header_without_vertical_thermal_gauges()
    test_wh40k_supersampled_visible_glyph_bounds_apply_optical_offset()
    test_military_logo_region_and_artwork_match_final_geometry()
    test_frozen_body_proposal_and_footer_contract_remains_unchanged()
    print("test_header_corrections_v71335 PASS")
