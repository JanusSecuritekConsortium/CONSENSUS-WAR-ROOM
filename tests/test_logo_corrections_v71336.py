from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for, header_logo_control_for
from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.components.header import logo_runtime_diagnostics, logo_text_control_from_box
from ui.components.telemetry_widgets import build_themed_telemetry, telemetry_control_signature
from ui.themes.catalog import THEMES


EXPECTED_LOGO_HASHES = {
    "eva": "5c10f1a59339b6a788880c4187481c0d3290abddc1dff9da80389fa8684df476",
    "wh40k": "dfe05107f652c009ef1c7a5efc6005adc82ceae42ff321870acdb67c21ec150c",
    "military": "cbbc12841faa0794c8653f6500dd00d117cfa28f77e2c66852e4ba776fd517b0",
}

EXPECTED_TELEMETRY_SIGNATURES_71335 = {
    "janus": ("Column", "column", 0, 0, False, True, 5, "janus_trace_v2"),
    "arasaka": ("Column", "column", 0, 2, False, False, 5, "arasaka_activity_bank_v2"),
    "eva": ("Column", "column", 0, 3, False, False, 4, "eva_magi_columns_v2"),
    "wh40k": ("Column", "column", 0, 4, False, False, 4, "wh40k_cogitator_v2"),
    "helldivers": ("Column", "column", 3, 0, False, False, 7, "helldivers_readiness_v2"),
    "military": ("Column", "column", 0, 0, True, False, 6, "military_matrix_v2"),
}


def _hash(theme_key: str) -> str:
    return hashlib.sha256(THEME_GRAPHIC_ASSETS[theme_key].logo_path.read_bytes()).hexdigest()


def test_eva_region_expands_without_clipping_or_asset_change() -> None:
    diagnostic = logo_runtime_diagnostics("eva", header_width=1920)
    left, right, top, bottom = diagnostic["clearances"]
    logo_box = build_layout_for("eva").content.controls[0].content.controls[0]
    viewport = logo_box.content.controls[0]

    assert _hash("eva") == EXPECTED_LOGO_HASHES["eva"]
    assert diagnostic["renderer_mode"] == "supersampled_rect"
    assert diagnostic["logo_region_width"] == 185
    assert diagnostic["logo_region_height"] == 168
    assert diagnostic["visible_artwork_width"] >= 172
    assert diagnostic["visible_artwork_height"] >= 148
    assert left >= 6
    assert right >= 6
    assert top >= 9
    assert bottom >= 9
    assert logo_box.clip_behavior == ft.ClipBehavior.HARD_EDGE
    assert viewport.clip_behavior == ft.ClipBehavior.HARD_EDGE
    assert diagnostic["optical_offset_x"] == 0


def test_wh40k_uses_theme_specific_optical_offset_only() -> None:
    diagnostic = logo_runtime_diagnostics("wh40k", header_width=1920)
    left, right, top, bottom = diagnostic["clearances"]

    assert _hash("wh40k") == EXPECTED_LOGO_HASHES["wh40k"]
    assert diagnostic["optical_offset_x"] == 6
    assert left >= 5
    assert right >= 5
    assert top >= 5
    assert bottom >= 5
    assert logo_runtime_diagnostics("eva", header_width=1920)["optical_offset_x"] == 0
    assert logo_runtime_diagnostics("military", header_width=1920)["optical_offset_x"] == 0


def test_military_uses_supersampled_square_renderer_with_exact_asset() -> None:
    diagnostic = logo_runtime_diagnostics("military", header_width=1920)
    left, right, top, bottom = diagnostic["clearances"]
    logo_box = build_layout_for("military").content.controls[0].content.controls[0]
    control = logo_text_control_from_box(logo_box)

    assert _hash("military") == EXPECTED_LOGO_HASHES["military"]
    assert diagnostic["renderer_mode"] == "supersampled_square"
    assert diagnostic["logo_region_width"] == 162
    assert 138 <= diagnostic["visible_artwork_width"] <= 144
    assert 148 <= diagnostic["visible_artwork_height"] <= 152
    assert left >= 10
    assert right >= 10
    assert top >= 6
    assert bottom >= 6
    assert logo_box.width == 162
    assert logo_box.content.scroll is None
    assert control.data["base_font_size"] >= 8
    assert control._Control__attrs["nowrap"][0] is True
    assert control.overflow == ft.TextOverflow.VISIBLE
    assert control.value == THEME_GRAPHIC_ASSETS["military"].logo_path.read_bytes().decode("utf-8")


def test_telemetry_control_signatures_remain_frozen_from_v71335() -> None:
    metrics = {
        "cpu": {"percent": 32.0},
        "ram": {"percent": 64.0},
        "disk": {"percent": 78.0},
        "gpu": {"usage_percent": 24.0, "vram_percent": 31.0},
        "thermal": {},
    }
    history = {"cpu": [32.0], "ram": [64.0], "gpu": [24.0], "cpu_temp": [], "gpu_temp": []}

    for theme_key, expected in EXPECTED_TELEMETRY_SIGNATURES_71335.items():
        control = build_themed_telemetry(theme_key, metrics, history, THEMES[theme_key])
        assert telemetry_control_signature(control) == expected


if __name__ == "__main__":
    test_eva_region_expands_without_clipping_or_asset_change()
    test_wh40k_uses_theme_specific_optical_offset_only()
    test_military_uses_supersampled_square_renderer_with_exact_asset()
    test_telemetry_control_signatures_remain_frozen_from_v71335()
    print("test_logo_corrections_v71336 PASS")
