from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import runtime_snapshot


def test_runtime_snapshot_includes_telemetry_and_visual_review() -> None:
    original_health = runtime_snapshot.health_check
    original_trace = runtime_snapshot.read_latest_trace
    original_telemetry = runtime_snapshot.sample_telemetry
    original_review = runtime_snapshot.manual_visual_review_summary
    try:
        runtime_snapshot.health_check = lambda _config, _nodes: {"status": "ready", "models": [], "missing_required_models": {}}
        runtime_snapshot.read_latest_trace = lambda: None
        runtime_snapshot.sample_telemetry = lambda _history: {
            "latest": {"cpu": {"percent": 1.0}, "gpu": {"status": "unavailable"}},
            "history": {"cpu": [1.0], "ram": [2.0], "gpu": [None]},
        }
        runtime_snapshot.manual_visual_review_summary = lambda: {
            "path": "reports/manual_visual_review_v7.10.9.json",
            "screenshot_status": "MANUAL_REVIEW_REQUIRED",
            "pending_count": 6,
            "action_required_count": 0,
            "themes": [],
        }

        snapshot = runtime_snapshot.build_runtime_snapshot()

        assert snapshot["telemetry"]["latest"]["cpu"]["percent"] == 1.0
        assert snapshot["screenshot_status"] == "MANUAL_REVIEW_REQUIRED"
        assert snapshot["visual_review"]["screenshot_status"] == "MANUAL_REVIEW_REQUIRED"
    finally:
        runtime_snapshot.health_check = original_health
        runtime_snapshot.read_latest_trace = original_trace
        runtime_snapshot.sample_telemetry = original_telemetry
        runtime_snapshot.manual_visual_review_summary = original_review


if __name__ == "__main__":
    test_runtime_snapshot_includes_telemetry_and_visual_review()
    print("test_runtime_snapshot_telemetry PASS")
