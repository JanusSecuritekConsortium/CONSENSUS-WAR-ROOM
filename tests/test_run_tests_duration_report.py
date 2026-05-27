from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_tests import build_duration_report


def test_duration_report_sorts_slowest_and_marks_gui_heavy() -> None:
    results = [
        {"file": "tests/test_fast.py", "duration_seconds": 1.0, "categories": ["FAST"], "gui_launch_heavy": False},
        {"file": "tests/test_gui_window_modes.py", "duration_seconds": 45.0, "categories": ["GUI", "SLOW"], "gui_launch_heavy": True},
        {"file": "tests/test_provider.py", "duration_seconds": 3.0, "categories": ["PROVIDER"], "gui_launch_heavy": False},
    ]

    report = build_duration_report(results, slow_threshold_seconds=30.0, total_budget_seconds=100.0)

    assert report["slowest_10"][0]["file"] == "tests/test_gui_window_modes.py"
    assert report["slow_tests"][0]["file"] == "tests/test_gui_window_modes.py"
    assert report["gui_launch_heavy_tests"][0]["file"] == "tests/test_gui_window_modes.py"


if __name__ == "__main__":
    test_duration_report_sorts_slowest_and_marks_gui_heavy()
    print("test_run_tests_duration_report PASS")
