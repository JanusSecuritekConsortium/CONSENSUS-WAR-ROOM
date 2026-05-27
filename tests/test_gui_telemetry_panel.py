from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.telemetry_panel import telemetry_summary_lines
from ui.flet_app import (
    build_command_palette,
    build_gui_layout,
    build_telemetry_snapshot_viewer,
    create_gui_state,
    execute_command_palette_action,
)


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "text") and isinstance(control.text, str):
        values.append(control.text)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def _noop(*_args, **_kwargs) -> None:
    return None


SAMPLE_TELEMETRY = {
    "latest": {
        "timestamp": "2026-05-27T00:00:00+00:00",
        "cpu": {"percent": 11.0},
        "ram": {"percent": 22.0},
        "gpu": {"status": "ready", "usage_percent": 33.0, "vram_percent": 44.0, "temperature_c": 55.0},
    },
    "history": {"cpu": [10.0, 11.0], "ram": [20.0, 22.0], "gpu": [30.0, 33.0]},
}


def test_telemetry_panel_uses_theme_specific_labels() -> None:
    assert "DEMOCRACY LOAD: 11.0%" in telemetry_summary_lines("helldivers", SAMPLE_TELEMETRY)
    assert "MACHINE SPIRIT LOAD: 11.0%" in telemetry_summary_lines("wh40k", SAMPLE_TELEMETRY)
    assert "FRONT-A CPU: 11.0%" in telemetry_summary_lines("janus", SAMPLE_TELEMETRY)


def test_gui_layout_contains_telemetry_without_body_ratio_change() -> None:
    state = create_gui_state("helldivers", RuntimeConfig(theme="helldivers", backend="mock"))
    state.telemetry_snapshot = SAMPLE_TELEMETRY
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    body = layout.content.controls[1].content
    text = "\n".join(_flatten_text(layout))

    assert [control.expand for control in body.controls] == [2, 6, 2]
    assert "TELEMETRY" in text
    assert "DEMOCRACY LOAD" in text


def test_command_palette_opens_telemetry_snapshot() -> None:
    state = create_gui_state("arasaka", RuntimeConfig(theme="arasaka", backend="mock"))
    palette = build_command_palette(state)

    assert "Telemetry Snapshot" in "\n".join(_flatten_text(palette))
    execute_command_palette_action(state, "Telemetry Snapshot")
    assert state.telemetry_viewer_open is True
    viewer = build_telemetry_snapshot_viewer(state)
    assert "TELEMETRY SNAPSHOT" in "\n".join(_flatten_text(viewer))


if __name__ == "__main__":
    test_telemetry_panel_uses_theme_specific_labels()
    test_gui_layout_contains_telemetry_without_body_ratio_change()
    test_command_palette_opens_telemetry_snapshot()
    print("test_gui_telemetry_panel PASS")
