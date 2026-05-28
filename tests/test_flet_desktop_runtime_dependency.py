from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.check_dependencies import REQUIRED_DEPENDENCIES
from ui import flet_app


def test_flet_desktop_is_declared_required_dependency() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "flet-desktop" in pyproject
    assert "flet" in pyproject
    assert "flet_desktop" in REQUIRED_DEPENDENCIES


def test_flet_desktop_runtime_preflight_has_actionable_error() -> None:
    original_find_spec = importlib.util.find_spec
    try:
        importlib.util.find_spec = lambda name, *args, **kwargs: None if name == "flet_desktop" else original_find_spec(name, *args, **kwargs)
        try:
            flet_app.ensure_flet_desktop_runtime()
        except RuntimeError as exc:
            message = str(exc)
        else:
            raise AssertionError("missing flet_desktop runtime did not fail")
    finally:
        importlib.util.find_spec = original_find_spec

    assert "Flet desktop runtime is not installed" in message
    assert "python -m pip install -e ." in message


def test_flet_desktop_runtime_present_in_current_environment() -> None:
    assert importlib.util.find_spec("flet_desktop") is not None


if __name__ == "__main__":
    test_flet_desktop_is_declared_required_dependency()
    test_flet_desktop_runtime_preflight_has_actionable_error()
    test_flet_desktop_runtime_present_in_current_environment()
    print("test_flet_desktop_runtime_dependency PASS")
