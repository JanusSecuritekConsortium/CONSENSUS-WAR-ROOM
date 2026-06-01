import tempfile
import zipfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import export_runtime_bundle


def test_bundle_contains_rss_intelligence_artifacts() -> None:
    original_snapshot = export_runtime_bundle.build_runtime_snapshot
    original_provider = export_runtime_bundle.build_provider_status_report
    original_trace = export_runtime_bundle.read_latest_trace
    original_dependencies = export_runtime_bundle.build_dependency_report
    try:
        export_runtime_bundle.build_runtime_snapshot = lambda: {"telemetry": {}, "data_sources_status": {"feeds": {}}, "rss_intelligence_status": {"mode": "RSS_PRIMARY"}}
        export_runtime_bundle.build_provider_status_report = lambda: {"provider": "msty", "status": "MOCK"}
        export_runtime_bundle.read_latest_trace = lambda: {}
        export_runtime_bundle.build_dependency_report = lambda: {"status": "MOCK"}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bundle.zip"
            export_runtime_bundle.export_runtime_bundle(target)
            with zipfile.ZipFile(target) as bundle:
                names = set(bundle.namelist())
            assert "rss_intelligence_status.json" in names
            assert "rss_intelligence_sample.json" in names
    finally:
        export_runtime_bundle.build_runtime_snapshot = original_snapshot
        export_runtime_bundle.build_provider_status_report = original_provider
        export_runtime_bundle.read_latest_trace = original_trace
        export_runtime_bundle.build_dependency_report = original_dependencies


if __name__ == "__main__":
    test_bundle_contains_rss_intelligence_artifacts()
    print("test_runtime_bundle_rss_backbone PASS")
