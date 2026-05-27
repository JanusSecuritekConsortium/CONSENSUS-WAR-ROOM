from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.telemetry_panel import telemetry_summary_lines


def test_gui_telemetry_lines_show_psutil_missing_degraded_state() -> None:
    telemetry = {
        "status": "DEGRADED",
        "degraded_reason": "psutil missing",
        "latest": {
            "cpu": {"status": "unavailable", "percent": None, "reason": "psutil missing"},
            "ram": {"status": "unavailable", "percent": None, "reason": "psutil missing"},
            "disk": {"status": "unavailable", "percent": None, "reason": "psutil missing"},
            "gpu": {"status": "unavailable", "usage_percent": None, "vram_percent": None},
        },
    }
    lines = telemetry_summary_lines("military", telemetry)

    assert "CPU LOAD: UNAVAILABLE" in lines
    assert "MEMORY: UNAVAILABLE" in lines
    assert "DISK: UNAVAILABLE" in lines
    assert "Reason: psutil missing" in lines


if __name__ == "__main__":
    test_gui_telemetry_lines_show_psutil_missing_degraded_state()
    print("test_gui_telemetry_degraded_message PASS")
