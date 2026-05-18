from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT_PY = {"main.py", "consensus_war_room_genesis.py"}


def test_root_contains_only_allowed_python_launchers() -> None:
    root_py = {path.name for path in ROOT.glob("*.py")}
    unexpected = sorted(root_py - ALLOWED_ROOT_PY)
    assert not unexpected, f"Unexpected root Python files: {', '.join(unexpected)}"


if __name__ == "__main__":
    test_root_contains_only_allowed_python_launchers()
    print("test_root_hygiene PASS")
