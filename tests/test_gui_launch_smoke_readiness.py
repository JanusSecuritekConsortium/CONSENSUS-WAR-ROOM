from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.gui_smoke_check import build_smoke_gui_state, run_control_tree_smoke, run_hidden_gui_smoke


def test_smoke_state_has_deterministic_readiness_marker() -> None:
    state = build_smoke_gui_state()

    assert state.heartbeat_text == "SMOKE READY"
    assert state.provider_status["status"] == "ready"
    assert state.telemetry_snapshot["source"] == "gui-smoke"


def test_control_tree_smoke_uses_smoke_state() -> None:
    assert run_control_tree_smoke() is True


def test_hidden_launch_smoke_returns_after_marker() -> None:
    assert run_hidden_gui_smoke(timeout=12.0) is True


if __name__ == "__main__":
    test_smoke_state_has_deterministic_readiness_marker()
    test_control_tree_smoke_uses_smoke_state()
    test_hidden_launch_smoke_returns_after_marker()
    print("test_gui_launch_smoke_readiness PASS")
