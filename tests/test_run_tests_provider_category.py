from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_tests


def test_msty_runtime_provider_file_is_not_fast() -> None:
    categories = run_tests.categorize_test(ROOT / "tests" / "test_msty_runtime.py")

    assert "PROVIDER" in categories
    assert "INTEGRATION" in categories
    assert "FAST" not in categories


def test_msty_runtime_fast_path_is_fast_only() -> None:
    categories = run_tests.categorize_test(ROOT / "tests" / "test_msty_runtime_fast_path.py")

    assert categories == {"FAST"}


def test_provider_selection_includes_msty_runtime_not_fast_path() -> None:
    tests = [
        ROOT / "tests" / "test_msty_runtime.py",
        ROOT / "tests" / "test_msty_runtime_fast_path.py",
    ]

    selected = run_tests.select_tests(tests, {"PROVIDER"})

    assert selected == [tests[0]]


if __name__ == "__main__":
    test_msty_runtime_provider_file_is_not_fast()
    test_msty_runtime_fast_path_is_fast_only()
    test_provider_selection_includes_msty_runtime_not_fast_path()
    print("test_run_tests_provider_category PASS")
