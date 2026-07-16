from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.components.header import (
    logo_runtime_diagnostics,
    logo_text_control_from_box,
    supersampled_logo_metrics,
    theme_logo_layout_mode,
)
from ui.components.telemetry_widgets import build_themed_telemetry, telemetry_control_signature
from ui.themes.catalog import THEMES


EXPECTED_EVA_GUI_HASH = "5c10f1a59339b6a788880c4187481c0d3290abddc1dff9da80389fa8684df476"
EVA_BOOT_HASH = "04786ec6cbfad90e20c91a4ff8e3de24ef056320734f4174add37631cf1069b8"
EXPECTED_TELEMETRY_SIGNATURES_71337 = {
    "janus": ("Column", "column", 0, 0, False, True, 5, "janus_trace_v2"),
    "arasaka": ("Column", "column", 0, 2, False, False, 5, "arasaka_activity_bank_v2"),
    "eva": ("Column", "column", 0, 3, False, False, 4, "eva_magi_columns_v2"),
    "wh40k": ("Column", "column", 0, 4, False, False, 4, "wh40k_cogitator_v2"),
    "helldivers": ("Column", "column", 3, 0, False, False, 7, "helldivers_readiness_v2"),
    "military": ("Column", "column", 0, 0, True, False, 6, "military_matrix_v2"),
}


def _eva_source() -> str:
    return THEME_GRAPHIC_ASSETS["eva"].logo_path.read_bytes().decode("utf-8")


def _eva_logo_box() -> ft.Container:
    layout = build_layout_for("eva")
    logo_box = layout.content.controls[0].content.controls[0]
    viewport = logo_box.content.controls[0]
    assert isinstance(viewport, ft.Stack)
    assert viewport.data["role"] == "supersampled_ascii_logo_viewport"
    return logo_box


def test_eva_uses_supersampled_renderer_with_exact_gui_source() -> None:
    source = _eva_source()
    logo_box = _eva_logo_box()
    viewport = logo_box.content.controls[0]
    canvas = viewport.controls[0]
    control = logo_text_control_from_box(logo_box)

    assert theme_logo_layout_mode(THEMES["eva"])["mode"] == "supersampled_rect"
    assert control.value == source
    assert control.data["layout_mode"] == "supersampled_rect"
    assert canvas.data["uniform_scale"] is True
    assert hashlib.sha256(THEME_GRAPHIC_ASSETS["eva"].logo_path.read_bytes()).hexdigest() == EXPECTED_EVA_GUI_HASH
    assert hashlib.sha256(THEME_GRAPHIC_ASSETS["eva"].logo_path.read_bytes()).hexdigest() != EVA_BOOT_HASH


def test_eva_supersampled_metrics_fill_wh40k_style_viewport() -> None:
    metrics = supersampled_logo_metrics(
        _eva_source(),
        base_font_size=10,
        cell_width=185,
        cell_height=168,
        line_height_factor=0.85,
    )
    left, right, top, bottom = metrics.clearances

    assert metrics.source_line_count == 56
    assert metrics.source_max_columns == 88
    assert metrics.cell_width == 185
    assert metrics.cell_height == 168
    assert metrics.base_font_size == 10
    assert 172 <= metrics.transformed_width <= 174
    assert 148 <= metrics.transformed_height <= 149
    assert left >= 6
    assert right >= 6
    assert top >= 9
    assert bottom >= 9


def test_eva_runtime_diagnostics_report_supersampled_containment() -> None:
    diagnostics = logo_runtime_diagnostics("eva", header_width=1920)
    left, right, top, bottom = diagnostics["clearances"]

    assert diagnostics["renderer_mode"] == "supersampled_rect"
    assert diagnostics["logo_region_width"] == 185
    assert diagnostics["logo_region_height"] == 168
    assert diagnostics["visible_artwork_width"] >= 172
    assert diagnostics["visible_artwork_height"] >= 148
    assert left >= 6
    assert right >= 6
    assert top >= 9
    assert bottom >= 9


def test_no_png_gui_logo_assets_exist() -> None:
    assert not list((ROOT / "static" / "logos" / "gui").glob("*.png"))


def test_telemetry_signatures_remain_unchanged_from_v71337() -> None:
    metrics = {
        "cpu": {"percent": 32.0},
        "ram": {"percent": 64.0},
        "disk": {"percent": 78.0},
        "gpu": {"usage_percent": 24.0, "vram_percent": 31.0},
        "thermal": {},
    }
    history = {"cpu": [32.0], "ram": [64.0], "gpu": [24.0], "cpu_temp": [], "gpu_temp": []}

    for theme_key, expected in EXPECTED_TELEMETRY_SIGNATURES_71337.items():
        control = build_themed_telemetry(theme_key, metrics, history, THEMES[theme_key])
        assert telemetry_control_signature(control) == expected
