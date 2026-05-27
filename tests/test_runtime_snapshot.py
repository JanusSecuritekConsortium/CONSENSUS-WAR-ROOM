from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from tools import runtime_snapshot


def test_runtime_snapshot_uses_real_provider_payload_shape() -> None:
    original_health = runtime_snapshot.health_check
    original_latest_trace = runtime_snapshot.read_latest_trace
    try:
        runtime_snapshot.health_check = lambda _config, _nodes: {
            "status": "degraded",
            "models": ["m1"],
            "missing_required_models": {"BELLATOR": "m2"},
            "degraded_reason": "models_missing",
        }
        runtime_snapshot.read_latest_trace = lambda: {"proposal_id": "p1", "final_verdict": "NO_CONSENSUS"}

        snapshot = runtime_snapshot.build_runtime_snapshot()

        assert snapshot["version"] == SYSTEM_VERSION
        assert snapshot["backend"] == "msty-local"
        assert snapshot["provider_status"] == "degraded"
        assert snapshot["active_models"] == ["m1"]
        assert snapshot["missing_models"] == {"BELLATOR": "m2"}
        assert snapshot["war_room_layout_guard"]["main_column_expand"] == [2, 6, 2]
        assert snapshot["render_guard_status"]["enabled"] is True
        assert snapshot["latest_decision_trace"]["proposal_id"] == "p1"
        assert snapshot["test_manifest_path"].endswith(f"verification_v{SYSTEM_VERSION}.json")
    finally:
        runtime_snapshot.health_check = original_health
        runtime_snapshot.read_latest_trace = original_latest_trace


if __name__ == "__main__":
    test_runtime_snapshot_uses_real_provider_payload_shape()
    print("test_runtime_snapshot PASS")
