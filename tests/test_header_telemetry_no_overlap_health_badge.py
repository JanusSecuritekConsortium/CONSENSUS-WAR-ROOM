from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.header import build_header
from ui.themes.catalog import get_gui_theme_options


def test_header_health_badge_and_telemetry_are_separate_rows() -> None:
    for theme in get_gui_theme_options():
        header = build_header(theme, "ready", "available")
        status_column = header.content.controls[1].content
        title_row, content_row = status_column.controls
        assert "HEALTH READY" in title_row.controls[1].content.value
        assert content_row.controls[1].data["role"] == "header_telemetry_panel"


if __name__ == "__main__":
    test_header_health_badge_and_telemetry_are_separate_rows()
    print("test_header_telemetry_no_overlap_health_badge PASS")
