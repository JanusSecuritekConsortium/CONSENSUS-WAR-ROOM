import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import runtime_snapshot


def test_runtime_snapshot_exposes_rss_primary_status() -> None:
    original_health = runtime_snapshot.health_check
    original_dependencies = runtime_snapshot.build_dependency_report
    original_telemetry = runtime_snapshot.sample_telemetry
    try:
        runtime_snapshot.health_check = lambda *_args, **_kwargs: {"status": "ready", "models": [], "missing_required_models": {}, "degraded_reason": None}
        runtime_snapshot.build_dependency_report = lambda: {"status": "MOCK"}
        runtime_snapshot.sample_telemetry = lambda *_args, **_kwargs: {"status": "MOCK"}
        snapshot = runtime_snapshot.build_runtime_snapshot()
        status = snapshot["rss_intelligence_status"]
        assert status["mode"] == "RSS_PRIMARY"
        assert status["poll_interval_seconds"] == 1200
        assert status["packet_item_limit"] == 12
        assert status["database_path"].endswith(r"_ARBITER\cache\data_sources\intelligence.db")
    finally:
        runtime_snapshot.health_check = original_health
        runtime_snapshot.build_dependency_report = original_dependencies
        runtime_snapshot.sample_telemetry = original_telemetry


if __name__ == "__main__":
    test_runtime_snapshot_exposes_rss_primary_status()
    print("test_runtime_snapshot_rss_backbone PASS")
