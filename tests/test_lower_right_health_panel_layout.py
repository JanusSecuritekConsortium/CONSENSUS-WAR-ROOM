from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for


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


def test_lower_right_panel_is_health_system_summary_not_telemetry() -> None:
    layout = build_layout_for("arasaka")
    right_column = layout.content.controls[1].content.controls[2].content
    health_region = right_column.controls[0]
    status_panel = health_region.content.controls[0]
    text = "\n".join(_flatten_text(status_panel))

    assert len(health_region.content.controls) == 1
    assert "SYSTEM STATUS" in text
    assert "PROVIDER" in text
    assert "ACTIVE MODELS" in text
    assert "LIFECYCLE" in text
    assert "TELEMETRY" not in text


if __name__ == "__main__":
    test_lower_right_panel_is_health_system_summary_not_telemetry()
    print("test_lower_right_health_panel_layout PASS")
