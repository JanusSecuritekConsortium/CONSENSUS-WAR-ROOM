from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.telemetry import TelemetryHistory, sparkline


def _sample(value: float) -> dict:
    return {
        "timestamp": "t",
        "cpu": {"percent": value},
        "ram": {"percent": value + 1},
        "gpu": {"usage_percent": value + 2},
    }


def test_telemetry_history_is_bounded() -> None:
    history = TelemetryHistory(max_samples=3, sampling_interval_seconds=1)
    for index in range(5):
        history.add_sample(_sample(float(index)))
    snapshot = history.snapshot()

    assert snapshot["max_samples"] == 3
    assert snapshot["history"]["cpu"] == [2.0, 3.0, 4.0]
    assert snapshot["history"]["ram"] == [3.0, 4.0, 5.0]
    assert snapshot["history"]["gpu"] == [4.0, 5.0, 6.0]


def test_telemetry_sparkline_is_text_only() -> None:
    line = sparkline([0, 50, 100], width=8)

    assert isinstance(line, str)
    assert line


if __name__ == "__main__":
    test_telemetry_history_is_bounded()
    test_telemetry_sparkline_is_text_only()
    print("test_telemetry_history PASS")
