from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from tools.runtime_snapshot import health_badge_from_snapshot
from ui.components.header import build_header
from ui.flet_app import create_gui_state


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def test_health_badge_from_runtime_snapshot_states() -> None:
    assert health_badge_from_snapshot({"provider_status": "ready", "missing_models": {}, "degraded_reason": None})[
        "label"
    ] == "READY"
    assert health_badge_from_snapshot(
        {"provider_status": "ready", "missing_models": {"BELLATOR": "m2"}, "degraded_reason": None}
    )["label"] == "DEGRADED"
    assert health_badge_from_snapshot({"provider_status": "unknown"})["label"] == "ERROR"


def test_header_renders_health_badge_without_shifting_telemetry_rows() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    header = build_header(
        state.theme,
        "ready",
        "AVAILABLE",
        "session-1",
        health_badge={"label": "READY", "color_role": "primary"},
    )
    text = "\n".join(_flatten_text(header))
    telemetry_labels = [row.controls[0].value for row in header.content.controls[1].content.controls[1:7]]

    assert "HEALTH READY" in text
    assert "ACTIVE MODE" in telemetry_labels
    assert "SESSION" in telemetry_labels


if __name__ == "__main__":
    test_health_badge_from_runtime_snapshot_states()
    test_header_renders_health_badge_without_shifting_telemetry_rows()
    print("test_health_badge PASS")
