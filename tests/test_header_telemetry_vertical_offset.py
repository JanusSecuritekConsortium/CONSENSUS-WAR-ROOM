from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.header import build_header
from ui.themes.catalog import THEMES


def test_header_status_content_is_raised_with_bottom_breathing_room() -> None:
    header = build_header(THEMES["arasaka"], "ready", "available")
    status_panel = header.content.controls[1]
    assert status_panel.data["role"] == "header_status_panel"
    assert status_panel.data["content_vertical_offset"] == "raised"
    assert status_panel.padding.top == 8
    assert status_panel.padding.bottom == 16


if __name__ == "__main__":
    test_header_status_content_is_raised_with_bottom_breathing_room()
    print("test_header_telemetry_vertical_offset PASS")
