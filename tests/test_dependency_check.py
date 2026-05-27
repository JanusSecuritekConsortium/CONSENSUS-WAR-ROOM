from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import check_dependencies


def test_dependency_report_shape_and_missing_required() -> None:
    original_module_status = check_dependencies._module_status
    original_which = check_dependencies.shutil.which
    try:
        check_dependencies._module_status = lambda name: {
            "name": name,
            "available": name not in {"psutil", "GPUtil"},
            "kind": "python_module",
            "origin": None,
        }
        check_dependencies.shutil.which = lambda _name: None

        report = check_dependencies.build_dependency_report()

        assert report["status"] == "ERROR"
        assert report["missing_required"] == ["psutil"]
        assert "GPUtil" in report["missing_optional"]
        assert "nvidia-smi" in report["missing_optional"]
        assert "python -m pip install -e ." in report["install_hints"]
    finally:
        check_dependencies._module_status = original_module_status
        check_dependencies.shutil.which = original_which


def test_dependency_report_ready_when_required_available() -> None:
    original_module_status = check_dependencies._module_status
    try:
        check_dependencies._module_status = lambda name: {
            "name": name,
            "available": True,
            "kind": "python_module",
            "origin": "test",
        }

        report = check_dependencies.build_dependency_report()

        assert report["status"] == "READY"
        assert report["missing_required"] == []
    finally:
        check_dependencies._module_status = original_module_status


if __name__ == "__main__":
    test_dependency_report_shape_and_missing_required()
    test_dependency_report_ready_when_required_available()
    print("test_dependency_check PASS")
