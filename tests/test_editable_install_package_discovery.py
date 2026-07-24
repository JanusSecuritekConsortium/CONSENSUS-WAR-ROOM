from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
REQUIREMENTS = ROOT / "requirements.txt"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _array_values(section: str, key: str) -> set[str]:
    text = PYPROJECT.read_text(encoding="utf-8")
    section_match = re.search(rf"^\[{re.escape(section)}\]\s*$", text, flags=re.MULTILINE)
    if not section_match:
        raise AssertionError(f"missing [{section}] section")
    body_start = section_match.end()
    next_section = re.search(r"^\[.+\]\s*$", text[body_start:], flags=re.MULTILINE)
    body = text[body_start : body_start + next_section.start()] if next_section else text[body_start:]
    key_match = re.search(rf"^{re.escape(key)}\s*=\s*\[(.*?)\]", body, flags=re.MULTILINE | re.DOTALL)
    if not key_match:
        raise AssertionError(f"missing {key} array in [{section}]")
    return set(re.findall(r'"([^"]+)"', key_match.group(1)))


def test_editable_install_has_explicit_setuptools_package_discovery() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")

    assert "[tool.setuptools.packages.find]" in text
    assert 'where = ["."]' in text


def test_active_packages_are_included_for_editable_install() -> None:
    include = _array_values("tool.setuptools.packages.find", "include")

    assert {
        "core*",
        "ui*",
        "config*",
        "integrations*",
        "voice*",
        "assistant*",
        "monoliths*",
    }.issubset(include)


def test_non_package_roots_are_excluded_from_editable_install() -> None:
    exclude = _array_values("tool.setuptools.packages.find", "exclude")

    assert {
        "archive*",
        "reports*",
        "external*",
        "static*",
        "future_implementations*",
        "tests*",
        "tools*",
        "logs*",
        "cache*",
        ".venv*",
        "venv*",
    }.issubset(exclude)


def test_runtime_dependencies_remain_declared() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")

    assert "psutil>=5.9" in text
    assert "requests>=2.31" in text
    assert "flet>=0.28.3,<0.29" in text
    assert "flet-desktop>=0.28.3,<0.29" in text
    assert "Pillow>=10.0" in text
    assert "fastapi>=0.115" in text
    assert "uvicorn>=0.30" in text
    assert "pydantic>=2.7" in text
    assert "websockets>=13,<16" in text
    assert "openai>=1.0" in text
    assert "python-dotenv>=1.0" in text
    assert "schedule>=1.2" in text
    assert "pyTelegramBotAPI>=4.20" in text
    assert "ib_insync" not in text


def test_legacy_requirements_match_gui_runtime_constraints() -> None:
    text = REQUIREMENTS.read_text(encoding="utf-8")

    assert "flet>=0.28.3,<0.29" in text
    assert "flet-desktop>=0.28.3,<0.29" in text
    assert "Pillow>=10.0" in text
    assert "fastapi>=0.115" in text
    assert "uvicorn>=0.30" in text
    assert "pydantic>=2.7" in text
    assert "websockets>=13,<16" in text


def test_ci_installs_canonical_project_with_dev_dependencies() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert 'python -m pip install -e ".[dev]"' in workflow
    assert "python -m pip install -r requirements-dev.txt" not in workflow


if __name__ == "__main__":
    test_editable_install_has_explicit_setuptools_package_discovery()
    test_active_packages_are_included_for_editable_install()
    test_non_package_roots_are_excluded_from_editable_install()
    test_runtime_dependencies_remain_declared()
    test_legacy_requirements_match_gui_runtime_constraints()
    test_ci_installs_canonical_project_with_dev_dependencies()
    print("test_editable_install_package_discovery PASS")
