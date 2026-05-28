from __future__ import annotations

import tempfile
import zipfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import export_runtime_bundle


def test_runtime_bundle_includes_proposal_history() -> None:
    original_snapshot = export_runtime_bundle.build_runtime_snapshot
    original_provider = export_runtime_bundle.build_provider_status_report
    original_trace = export_runtime_bundle.read_latest_trace
    original_dependency_report = export_runtime_bundle.build_dependency_report
    try:
        export_runtime_bundle.build_runtime_snapshot = lambda: {
            "version": "TEST",
            "provider_status": "ready",
            "health_badge": {"label": "READY"},
            "telemetry": {},
            "screenshot_status": "MANUAL_REVIEW_REQUIRED",
        }
        export_runtime_bundle.build_provider_status_report = lambda: {"provider": "msty", "backend": "msty-local"}
        export_runtime_bundle.read_latest_trace = lambda: {}
        export_runtime_bundle.build_dependency_report = lambda: {"missing_required": [], "missing_optional": []}
        with tempfile.TemporaryDirectory() as tmp:
            bundle_path = export_runtime_bundle.export_runtime_bundle(Path(tmp) / "bundle.zip")
            with zipfile.ZipFile(bundle_path) as bundle:
                names = set(bundle.namelist())
            assert "proposal_history_status.json" in names
            assert "reports/proposal_history.jsonl" in names
    finally:
        export_runtime_bundle.build_runtime_snapshot = original_snapshot
        export_runtime_bundle.build_provider_status_report = original_provider
        export_runtime_bundle.read_latest_trace = original_trace
        export_runtime_bundle.build_dependency_report = original_dependency_report


if __name__ == "__main__":
    test_runtime_bundle_includes_proposal_history()
    print("test_runtime_bundle_proposals PASS")
