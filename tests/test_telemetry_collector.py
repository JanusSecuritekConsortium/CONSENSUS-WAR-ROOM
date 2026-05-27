from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import telemetry


def test_collect_system_telemetry_returns_structured_payload() -> None:
    original_gpu = telemetry.collect_gpu_telemetry
    try:
        telemetry.collect_gpu_telemetry = lambda: {
            "status": "ready",
            "source": "test",
            "usage_percent": 12.5,
            "vram_percent": 33.0,
            "temperature_c": 44.0,
        }
        sample = telemetry.collect_system_telemetry(ROOT)

        assert "timestamp" in sample
        assert sample["cpu"]["status"] in {"ready", "unavailable"}
        assert sample["ram"]["status"] in {"ready", "unavailable"}
        assert sample["disk"]["status"] in {"ready", "unavailable"}
        assert sample["gpu"]["usage_percent"] == 12.5
    finally:
        telemetry.collect_gpu_telemetry = original_gpu


if __name__ == "__main__":
    test_collect_system_telemetry_returns_structured_payload()
    print("test_telemetry_collector PASS")
