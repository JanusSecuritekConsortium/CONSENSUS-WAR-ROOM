from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import telemetry


def test_gpu_telemetry_unavailable_never_crashes() -> None:
    original_nvidia = telemetry._gpu_from_nvidia_smi
    original_gputil = telemetry._gpu_from_gputil
    try:
        telemetry._gpu_from_nvidia_smi = lambda: (_ for _ in ()).throw(RuntimeError("no nvidia"))
        telemetry._gpu_from_gputil = lambda: (_ for _ in ()).throw(RuntimeError("no gputil"))

        gpu = telemetry.collect_gpu_telemetry()

        assert gpu["status"] == "unavailable"
        assert gpu["usage_percent"] is None
        assert gpu["vram_percent"] is None
    finally:
        telemetry._gpu_from_nvidia_smi = original_nvidia
        telemetry._gpu_from_gputil = original_gputil


if __name__ == "__main__":
    test_gpu_telemetry_unavailable_never_crashes()
    print("test_telemetry_no_gpu_available PASS")
