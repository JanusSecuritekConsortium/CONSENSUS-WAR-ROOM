from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import export_runtime_bundle


def test_runtime_bundle_includes_active_manifest_and_integrity_result() -> None:
    original_snapshot = export_runtime_bundle.build_runtime_snapshot
    original_provider = export_runtime_bundle.build_provider_status_report
    original_trace = export_runtime_bundle.read_latest_trace
    original_latest_manifest = export_runtime_bundle.latest_active_manifest
    original_verify = export_runtime_bundle.verify_active_manifest
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active_manifest = root / "active_manifest_TEST.json"
            active_manifest.write_text('{"version":"TEST","files":[]}\n', encoding="utf-8")

            export_runtime_bundle.build_runtime_snapshot = lambda: {"version": "TEST"}
            export_runtime_bundle.build_provider_status_report = lambda: {"provider": "msty"}
            export_runtime_bundle.read_latest_trace = lambda: {"proposal_id": "p1"}
            export_runtime_bundle.latest_active_manifest = lambda: active_manifest
            export_runtime_bundle.verify_active_manifest = lambda _manifest=None: {
                "status": "CLEAN",
                "manifest_path": str(active_manifest),
            }

            target = root / "runtime_bundle.zip"
            export_runtime_bundle.export_runtime_bundle(target, log_lines=1)
            with zipfile.ZipFile(target) as bundle:
                names = set(bundle.namelist())
                integrity = bundle.read("integrity_verification.json").decode("utf-8")

        assert "integrity_verification.json" in names
        assert "reports/active_manifest_TEST.json" in names
        assert '"status": "CLEAN"' in integrity
    finally:
        export_runtime_bundle.build_runtime_snapshot = original_snapshot
        export_runtime_bundle.build_provider_status_report = original_provider
        export_runtime_bundle.read_latest_trace = original_trace
        export_runtime_bundle.latest_active_manifest = original_latest_manifest
        export_runtime_bundle.verify_active_manifest = original_verify


if __name__ == "__main__":
    test_runtime_bundle_includes_active_manifest_and_integrity_result()
    print("test_runtime_bundle_integrity PASS")
