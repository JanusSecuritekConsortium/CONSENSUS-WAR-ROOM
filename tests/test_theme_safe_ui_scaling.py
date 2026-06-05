from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.components.header import header_logo_layout, header_logo_text, logo_text_control_from_box
from ui.components.status_panel import build_status_panel
from ui.themes.catalog import GUI_THEME_KEYS, THEMES


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def test_gui_header_registry_uses_only_gui_logo_assets() -> None:
    gui_root = ROOT / "static" / "logos" / "gui"
    for theme_key in GUI_THEME_KEYS:
        asset = THEME_GRAPHIC_ASSETS[theme_key]
        assert asset.logo_path.parent == gui_root
        assert asset.logo_path.name == f"{theme_key}_header.txt"


def test_header_logo_uses_full_asset_or_explicit_fallback_only() -> None:
    for theme_key in GUI_THEME_KEYS:
        theme = THEMES[theme_key]
        asset = THEME_GRAPHIC_ASSETS[theme_key]
        rendered = header_logo_text(theme)
        full = read_normalized_logo(asset.logo_path).text if theme_key not in {"eva", "helldivers"} else asset.logo_path.read_text(encoding="utf-8")
        explicit_fallbacks = []
        for suffix in ("compact", "micro"):
            path = asset.logo_path.with_name(f"{asset.logo_path.stem}_{suffix}{asset.logo_path.suffix}")
            if path.exists():
                explicit_fallbacks.append(path.read_text(encoding="utf-8"))

        assert rendered == full or rendered in explicit_fallbacks or rendered == "[LOGO TOO LARGE]"


def test_rendered_header_logo_matches_safe_header_text_all_themes() -> None:
    for theme_key in GUI_THEME_KEYS:
        layout = build_layout_for(theme_key)
        logo_box = layout.content.controls[0].content.controls[0]
        logo_text = logo_text_control_from_box(logo_box).value

        assert logo_text == header_logo_text(THEMES[theme_key])
        assert logo_text.strip()


def test_header_telemetry_is_bounded_and_health_badge_reserved() -> None:
    for theme_key in GUI_THEME_KEYS:
        layout = build_layout_for(theme_key)
        header = layout.content.controls[0]
        status_panel = header.content.controls[1]
        top_row = status_panel.content.controls[0]
        telemetry = next(
            control
            for control in _walk(header)
            if getattr(control, "data", None)
            and isinstance(getattr(control, "data", None), dict)
            and getattr(control, "data", {}).get("role") == "header_telemetry_panel"
        )

        assert len(top_row.controls) == 2
        assert "HEALTH" in top_row.controls[1].content.value
        assert telemetry.data["bounded"] is True
        assert telemetry.data["summary_lines"] <= 5
        assert telemetry.data["graph_lines"] <= 1
        assert telemetry.height is not None
        assert telemetry.clip_behavior == ft.ClipBehavior.HARD_EDGE


def test_header_status_and_telemetry_remain_readable() -> None:
    for theme_key in GUI_THEME_KEYS:
        layout = build_layout_for(theme_key)
        header = layout.content.controls[0]
        status_panel = header.content.controls[1]
        title_row = status_panel.content.controls[0]
        content_row = status_panel.content.controls[1]
        status_column = content_row.controls[0]
        telemetry = content_row.controls[1]

        assert title_row.controls[0].size >= 16
        for row in status_column.controls:
            if isinstance(row, ft.Row):
                for control in row.controls:
                    if isinstance(control, ft.Text):
                        assert control.size >= 12
        for control in telemetry.content.controls:
            if isinstance(control, ft.Text):
                minimum = 12 if control.value == "LIVE TELEMETRY" else 10
                assert control.size >= minimum


def test_wh40k_uses_larger_header_telemetry_without_global_scaling() -> None:
    sizes_by_theme = {}
    for theme_key in GUI_THEME_KEYS:
        layout = build_layout_for(theme_key)
        header = layout.content.controls[0]
        telemetry = header.content.controls[1].content.controls[1].controls[1]
        sizes_by_theme[theme_key] = [
            control.size for control in telemetry.content.controls if isinstance(control, ft.Text)
        ]

    assert max(sizes_by_theme["wh40k"]) > max(sizes_by_theme["helldivers"])
    assert max(sizes_by_theme["helldivers"]) >= 12


def test_janus_header_offset_is_metadata_driven() -> None:
    layout = header_logo_layout(THEMES["janus"])

    assert layout.logo_offset_x < 0
    assert layout.logo_offset_y >= 0


def test_right_status_panel_wraps_long_activity_without_overflow() -> None:
    panel = build_status_panel(
        THEMES["helldivers"],
        {"status": "ready"},
        "AVAILABLE",
        ambient_status="DEMOCRATIC AUTHORIZATION STANDBY WITH EXTENDED STRATEGIC LIBERTY COMMAND ACTIVITY STRING",
    )
    activity_rows = [
        control
        for control in _walk(panel)
        if isinstance(control, ft.Text) and "ACTIVITY:" in str(getattr(control, "value", ""))
    ]

    assert panel.data["bounded_text"] is True
    assert panel.clip_behavior == ft.ClipBehavior.HARD_EDGE
    assert activity_rows
    assert activity_rows[0].max_lines == 2


if __name__ == "__main__":
    test_gui_header_registry_uses_only_gui_logo_assets()
    test_header_logo_uses_full_asset_or_explicit_fallback_only()
    test_rendered_header_logo_matches_safe_header_text_all_themes()
    test_header_telemetry_is_bounded_and_health_badge_reserved()
    test_header_status_and_telemetry_remain_readable()
    test_wh40k_uses_larger_header_telemetry_without_global_scaling()
    test_janus_header_offset_is_metadata_driven()
    test_right_status_panel_wraps_long_activity_without_overflow()
    print("test_theme_safe_ui_scaling PASS")
