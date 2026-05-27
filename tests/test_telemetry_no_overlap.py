from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.telemetry_panel import TELEMETRY_MAX_SUMMARY_LINES, TELEMETRY_PANEL_HEIGHT, build_telemetry_panel
from ui.themes.catalog import THEMES


def test_telemetry_panel_has_fixed_height_and_line_limit() -> None:
    telemetry = {
        "latest": {
            "cpu": {"percent": 1},
            "ram": {"percent": 2},
            "disk": {"percent": 3},
            "gpu": {"status": "ready", "usage_percent": 4, "vram_percent": 5, "temperature_c": 60},
        },
        "history": {"cpu": [1, 2], "gpu": [4, 5]},
    }
    panel = build_telemetry_panel(THEMES["helldivers"], telemetry)
    text_count = sum(1 for control in panel.content.controls if hasattr(control, "value"))

    assert panel.height == TELEMETRY_PANEL_HEIGHT
    assert panel.expand is False
    assert panel.content.scroll is None
    assert text_count <= 1 + TELEMETRY_MAX_SUMMARY_LINES + 3


if __name__ == "__main__":
    test_telemetry_panel_has_fixed_height_and_line_limit()
    print("test_telemetry_no_overlap PASS")
