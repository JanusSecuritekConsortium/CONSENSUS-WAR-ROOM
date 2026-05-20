from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.active_compile import compile_active_sources, iter_active_python_sources


def test_active_sources_exclude_legacy_boundaries() -> None:
    sources = [path.relative_to(ROOT) for path in iter_active_python_sources(ROOT)]
    assert sources
    assert any(path.parts[0] == "assistant" for path in sources)
    assert any(path.parts[0] == "voice" for path in sources)
    assert not any("archive" in path.parts for path in sources)
    assert not any("_ARBITER" in path.parts for path in sources)
    assert not any("__pycache__" in path.parts for path in sources)
    assert not any("external" in path.parts for path in sources)
    assert any(path.parts[0] == "tools" for path in sources)


def test_active_sources_compile() -> None:
    result = compile_active_sources(ROOT)
    assert result.ok, "\n".join(result.failures)
    assert result.compiled
    assert result.skipped_directories


def test_compile_active_tree_script_exists() -> None:
    script = ROOT / "tools" / "compile_active_tree.py"
    assert script.exists()
    assert script.read_text(encoding="utf-8").count("compile_active_sources") >= 1


if __name__ == "__main__":
    test_active_sources_exclude_legacy_boundaries()
    test_active_sources_compile()
    test_compile_active_tree_script_exists()
    print("test_active_compile PASS")
