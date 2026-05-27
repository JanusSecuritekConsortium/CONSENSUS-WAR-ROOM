from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_tests import build_duration_report


def test_budget_warnings_do_not_imply_failure_by_themselves() -> None:
    report = build_duration_report(
        [{"file": "tests/test_slow.py", "duration_seconds": 31.0, "categories": ["SLOW"], "gui_launch_heavy": False}],
        slow_threshold_seconds=30.0,
        total_budget_seconds=30.0,
    )

    assert any("slow_test:" in warning for warning in report["warnings"])
    assert any("total_budget:" in warning for warning in report["warnings"])


if __name__ == "__main__":
    test_budget_warnings_do_not_imply_failure_by_themselves()
    print("test_run_tests_budget_warning PASS")
