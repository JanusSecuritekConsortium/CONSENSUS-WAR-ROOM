from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import export_runtime_bundle


def test_runtime_bundle_contains_operator_artifacts() -> None:
    original_snapshot = export_runtime_bundle.build_runtime_snapshot
    original_provider = export_runtime_bundle.build_provider_status_report
    original_trace = export_runtime_bundle.read_latest_trace
    original_visual_review = export_runtime_bundle.manual_visual_review_summary
    original_dependency_report = export_runtime_bundle.build_dependency_report
    try:
        export_runtime_bundle.build_runtime_snapshot = lambda: {
            "version": "TEST",
            "provider_status": "ready",
            "health_badge": {"label": "READY"},
            "screenshot_status": "MANUAL_REVIEW_REQUIRED",
            "telemetry": {"latest": {"cpu": {"percent": 1}}},
        }
        export_runtime_bundle.build_provider_status_report = lambda: {
            "provider": "msty",
            "backend": "msty-local",
        }
        export_runtime_bundle.read_latest_trace = lambda: {
            "proposal_id": "proposal-1",
            "final_verdict": "APPROVED",
        }
        export_runtime_bundle.manual_visual_review_summary = lambda _path=None: {
            "screenshot_status": "MANUAL_REVIEW_REQUIRED",
            "pending_count": 6,
            "action_required_count": 0,
            "themes": [],
        }
        export_runtime_bundle.build_dependency_report = lambda: {
            "missing_required": [],
            "missing_optional": ["GPUtil"],
        }

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "runtime_bundle.zip"
            result = export_runtime_bundle.export_runtime_bundle(target, log_lines=1)

            assert result == target
            assert target.exists()
            with zipfile.ZipFile(target) as bundle:
                names = set(bundle.namelist())

        assert "runtime_snapshot.json" in names
        assert "provider_status.json" in names
        assert "latest_decision_trace.json" in names
        assert "manual_visual_review_summary.json" in names
        assert "telemetry_summary.json" in names
        assert "dependency_status.json" in names
        assert "logs/system_tail.jsonl" in names
        assert "logs/war_room_runtime_tail.jsonl" in names
        assert "CHANGELOG_excerpt.md" in names
        assert "manifest.json" in names
    finally:
        export_runtime_bundle.build_runtime_snapshot = original_snapshot
        export_runtime_bundle.build_provider_status_report = original_provider
        export_runtime_bundle.read_latest_trace = original_trace
        export_runtime_bundle.manual_visual_review_summary = original_visual_review
        export_runtime_bundle.build_dependency_report = original_dependency_report


if __name__ == "__main__":
    test_runtime_bundle_contains_operator_artifacts()
    print("test_runtime_bundle_export PASS")
