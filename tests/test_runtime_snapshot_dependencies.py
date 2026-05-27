from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import runtime_snapshot


def test_runtime_snapshot_includes_dependency_status_and_telemetry_reason() -> None:
    original_health = runtime_snapshot.health_check
    original_trace = runtime_snapshot.read_latest_trace
    original_deps = runtime_snapshot.build_dependency_report
    original_telemetry = runtime_snapshot.sample_telemetry
    try:
        runtime_snapshot.health_check = lambda _config, _nodes: {"status": "ready", "models": [], "missing_required_models": {}}
        runtime_snapshot.read_latest_trace = lambda: None
        runtime_snapshot.build_dependency_report = lambda: {
            "required_dependencies": {"psutil": {"available": False}},
            "optional_dependencies": {"GPUtil": {"available": False}},
            "missing_required": ["psutil"],
            "missing_optional": ["GPUtil"],
        }
        runtime_snapshot.sample_telemetry = lambda _history: {
            "status": "DEGRADED",
            "degraded_reason": "psutil missing",
            "latest": {"status": "DEGRADED", "degraded_reason": "psutil missing"},
            "history": {"cpu": [], "ram": [], "gpu": []},
        }

        snapshot = runtime_snapshot.build_runtime_snapshot()

        assert snapshot["dependency_status"]["missing_required"] == ["psutil"]
        assert snapshot["telemetry"]["status"] == "DEGRADED"
        assert snapshot["telemetry"]["degraded_reason"] == "psutil missing"
    finally:
        runtime_snapshot.health_check = original_health
        runtime_snapshot.read_latest_trace = original_trace
        runtime_snapshot.build_dependency_report = original_deps
        runtime_snapshot.sample_telemetry = original_telemetry


if __name__ == "__main__":
    test_runtime_snapshot_includes_dependency_status_and_telemetry_reason()
    print("test_runtime_snapshot_dependencies PASS")
