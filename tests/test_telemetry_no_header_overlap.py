from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for


def test_header_telemetry_does_not_overlap_health_badge_or_status_fields() -> None:
    header = build_layout_for("wh40k").content.controls[0]
    status_panel = header.content.controls[1]
    title_row = status_panel.content.controls[0]
    status_and_telemetry = status_panel.content.controls[1]
    status_column = status_and_telemetry.controls[0]
    telemetry_box = status_and_telemetry.controls[1]

    assert title_row.controls[1].content.value.startswith("HEALTH ")
    assert telemetry_box.width < status_panel.width if status_panel.width else telemetry_box.width <= 460
    assert status_column.expand == 1
    assert telemetry_box.clip_behavior is not None
    assert telemetry_box.content.scroll is None


if __name__ == "__main__":
    test_header_telemetry_does_not_overlap_health_badge_or_status_fields()
    print("test_telemetry_no_header_overlap PASS")
