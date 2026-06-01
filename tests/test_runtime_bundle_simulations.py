from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import export_runtime_bundle


def test_runtime_bundle_includes_simulation_status_and_history() -> None:
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
            target = Path(tmp) / "bundle.zip"
            export_runtime_bundle.export_runtime_bundle(target)
            with zipfile.ZipFile(target) as bundle:
                names = set(bundle.namelist())
            assert "simulation_status.json" in names
            assert "simulation_dossier_status.json" in names
            assert "reports/simulation_history.jsonl" in names
    finally:
        export_runtime_bundle.build_runtime_snapshot = original_snapshot
        export_runtime_bundle.build_provider_status_report = original_provider
        export_runtime_bundle.read_latest_trace = original_trace
        export_runtime_bundle.build_dependency_report = original_dependency_report


if __name__ == "__main__":
    test_runtime_bundle_includes_simulation_status_and_history()
    print("test_runtime_bundle_simulations PASS")
