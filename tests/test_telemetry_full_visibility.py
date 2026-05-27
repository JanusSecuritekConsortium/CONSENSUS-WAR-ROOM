from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.telemetry_panel import TELEMETRY_MAX_SUMMARY_LINES, telemetry_summary_lines


SAMPLE = {
    "latest": {
        "cpu": {"percent": 11},
        "ram": {"percent": 22},
        "disk": {"percent": 33},
        "gpu": {"status": "ready", "usage_percent": 44, "vram_percent": 55, "temperature_c": 66},
    },
    "history": {"cpu": [11, 12], "gpu": [44, 45]},
}


def test_telemetry_summary_shows_all_core_metrics() -> None:
    lines = telemetry_summary_lines("military", SAMPLE)
    text = "\n".join(lines)

    for token in ("CPU LOAD", "MEMORY", "DISK", "GPU LOAD", "VRAM", "GPU TEMP"):
        assert token in text
    assert len(lines) <= TELEMETRY_MAX_SUMMARY_LINES


if __name__ == "__main__":
    test_telemetry_summary_shows_all_core_metrics()
    print("test_telemetry_full_visibility PASS")
