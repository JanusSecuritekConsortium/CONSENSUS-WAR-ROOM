from __future__ import annotations

import builtins
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import telemetry


def test_telemetry_reports_degraded_when_psutil_missing() -> None:
    original_import = builtins.__import__
    original_gpu = telemetry.collect_gpu_telemetry

    def fake_import(name, *args, **kwargs):
        if name == "psutil":
            raise ModuleNotFoundError("No module named 'psutil'", name="psutil")
        return original_import(name, *args, **kwargs)

    try:
        builtins.__import__ = fake_import
        telemetry.collect_gpu_telemetry = lambda: {
            "status": "unavailable",
            "source": "test",
            "usage_percent": None,
            "vram_percent": None,
            "temperature_c": None,
        }

        sample = telemetry.collect_system_telemetry(ROOT)

        assert sample["status"] == "DEGRADED"
        assert sample["degraded_reason"] == "psutil missing"
        assert sample["cpu"]["reason"] == "psutil missing"
        assert sample["ram"]["reason"] == "psutil missing"
        assert sample["disk"]["reason"] == "psutil missing"
        assert "python -m pip install psutil" in sample["install_hints"]
    finally:
        builtins.__import__ = original_import
        telemetry.collect_gpu_telemetry = original_gpu


if __name__ == "__main__":
    test_telemetry_reports_degraded_when_psutil_missing()
    print("test_telemetry_degraded_psutil_missing PASS")
