from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_tests import build_duration_report, write_manifest


def test_verification_manifest_includes_duration_report(tmp_path: Path) -> None:
    results = [
        {
            "file": "tests/test_gui_window_modes.py",
            "status": "pass",
            "returncode": 0,
            "duration_seconds": 45.0,
            "categories": ["GUI", "SLOW"],
            "gui_launch_heavy": True,
            "stdout": "",
            "stderr": "",
        }
    ]
    report = build_duration_report(results, slow_threshold_seconds=30.0, total_budget_seconds=100.0)
    target = tmp_path / "verification.json"

    manifest = write_manifest(results, target, ["GUI"], report)
    written = json.loads(target.read_text(encoding="utf-8"))

    assert manifest["duration_report"]["slowest_10"][0]["file"] == "tests/test_gui_window_modes.py"
    assert written["gui_launch_heavy_tests"][0]["file"] == "tests/test_gui_window_modes.py"
    assert written["selected_categories"] == ["GUI"]


def test_verification_manifest_includes_duration_comparison_when_previous_exists(tmp_path: Path) -> None:
    previous_results = [
        {
            "file": "tests/test_gui_window_modes.py",
            "status": "pass",
            "returncode": 0,
            "duration_seconds": 45.0,
            "categories": ["GUI", "SLOW"],
            "gui_launch_heavy": True,
            "stdout": "",
            "stderr": "",
        }
    ]
    target = tmp_path / "verification_v7.10.12.json"
    target.write_text(
        json.dumps(
            {
                "version": "7.10.11",
                "duration_seconds": 45.0,
                "duration_report": {"total_duration_seconds": 45.0},
                "tests": previous_results,
            }
        ),
        encoding="utf-8",
    )
    current_results = [{**previous_results[0], "duration_seconds": 5.0}]
    report = build_duration_report(current_results, slow_threshold_seconds=30.0, total_budget_seconds=100.0)

    manifest = write_manifest(current_results, target, ["GUI"], report)

    comparison = manifest["duration_comparison"]
    assert comparison["baseline_version"] == "7.10.11"
    assert comparison["tests_compared"] == 1
    assert comparison["improved_10"][0]["delta_seconds"] == -40.0


if __name__ == "__main__":
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        test_verification_manifest_includes_duration_report(Path(tmp))
    with TemporaryDirectory() as tmp:
        test_verification_manifest_includes_duration_comparison_when_previous_exists(Path(tmp))
    print("test_verification_manifest_durations PASS")
