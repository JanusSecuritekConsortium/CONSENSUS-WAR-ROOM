from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_tests


def test_category_detection_from_names() -> None:
    gui = ROOT / "tests" / "test_gui_layout_contract.py"
    provider = ROOT / "tests" / "test_provider_discovery.py"
    fast = ROOT / "tests" / "test_prompt_assembly.py"

    assert "GUI" in run_tests.categorize_test(gui)
    assert "PROVIDER" in run_tests.categorize_test(provider)
    assert "FAST" in run_tests.categorize_test(fast)


def test_select_tests_filters_by_category() -> None:
    tests = [
        ROOT / "tests" / "test_gui_layout_contract.py",
        ROOT / "tests" / "test_provider_discovery.py",
        ROOT / "tests" / "test_prompt_assembly.py",
    ]

    selected = run_tests.select_tests(tests, {"GUI"})

    assert selected == [tests[0]]


def test_gui_harness_refactored_tests_are_not_marked_launch_heavy() -> None:
    metadata = run_tests.test_metadata(ROOT / "tests" / "test_gui_window_modes.py")

    assert "GUI" in metadata["categories"]
    assert metadata["gui_launch_heavy"] is False


if __name__ == "__main__":
    test_category_detection_from_names()
    test_select_tests_filters_by_category()
    test_gui_harness_refactored_tests_are_not_marked_launch_heavy()
    print("test_run_tests_categories PASS")
