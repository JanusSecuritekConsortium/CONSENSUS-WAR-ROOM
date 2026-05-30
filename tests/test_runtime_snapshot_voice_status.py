from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import runtime_snapshot


def test_runtime_snapshot_includes_arbiter_voice_status() -> None:
    original_health = runtime_snapshot.health_check
    original_trace = runtime_snapshot.read_latest_trace
    original_voice = runtime_snapshot.voice_status_snapshot
    try:
        runtime_snapshot.health_check = lambda _config, _nodes: {"status": "ready", "models": [], "missing_required_models": {}}
        runtime_snapshot.read_latest_trace = lambda: None
        runtime_snapshot.voice_status_snapshot = lambda: {
            "status": "ENABLED",
            "backend": "ARBITER_GLADOS",
            "last_voice_announcement": {"proposal_id": "p1", "verdict": "NO_CONSENSUS", "status": "success"},
        }

        snapshot = runtime_snapshot.build_runtime_snapshot()

        assert snapshot["voice_status"]["backend"] == "ARBITER_GLADOS"
        assert snapshot["voice_status"]["last_voice_announcement"]["proposal_id"] == "p1"
    finally:
        runtime_snapshot.health_check = original_health
        runtime_snapshot.read_latest_trace = original_trace
        runtime_snapshot.voice_status_snapshot = original_voice


if __name__ == "__main__":
    test_runtime_snapshot_includes_arbiter_voice_status()
    print("test_runtime_snapshot_voice_status PASS")
