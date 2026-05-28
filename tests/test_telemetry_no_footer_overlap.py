from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.telemetry_panel import TELEMETRY_PANEL_HEIGHT


def test_telemetry_stays_inside_right_column_above_log_panel() -> None:
    layout = build_layout_for("military")
    right_column = layout.content.controls[1].content.controls[2].content
    assert right_column.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
    status_and_telemetry = right_column.controls[0]
    assert status_and_telemetry.content.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
    telemetry_panel = status_and_telemetry.content.controls[1]
    log_panel = right_column.controls[1]

    assert telemetry_panel.height == TELEMETRY_PANEL_HEIGHT
    assert telemetry_panel.expand is False
    assert log_panel.expand is True
    assert right_column.spacing >= 12


if __name__ == "__main__":
    test_telemetry_stays_inside_right_column_above_log_panel()
    print("test_telemetry_no_footer_overlap PASS")
