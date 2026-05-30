from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for


def test_lower_right_column_keeps_health_panel_above_log_panel() -> None:
    layout = build_layout_for("military")
    right_column = layout.content.controls[1].content.controls[2].content
    assert right_column.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
    health_panel_region = right_column.controls[0]
    log_panel = right_column.controls[1]

    assert health_panel_region.content.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
    assert len(health_panel_region.content.controls) == 1
    assert "SYSTEM STATUS" in health_panel_region.content.controls[0].content.controls[0].controls[0].value
    assert log_panel.expand is True
    assert right_column.spacing >= 12


if __name__ == "__main__":
    test_lower_right_column_keeps_health_panel_above_log_panel()
    print("test_telemetry_no_footer_overlap PASS")
