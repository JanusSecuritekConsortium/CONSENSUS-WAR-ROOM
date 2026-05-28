from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import create_gui_state, runtime_snapshot_from_gui_state, submit_proposal_live_for_gui


def test_gui_runtime_snapshot_includes_active_tribunal_lifecycle() -> None:
    state = create_gui_state("arasaka", RuntimeConfig(theme="arasaka", backend="mock"))
    submit_proposal_live_for_gui(state, "Approve lifecycle snapshot coverage.", skip_animations=True)
    lifecycle = runtime_snapshot_from_gui_state(state)["tribunal_lifecycle"]

    assert lifecycle["current_phase"] == "EXPORT_READY"
    assert lifecycle["event_count"] >= 6
    assert 0.0 <= lifecycle["convergence_percent"] <= 1.0
    assert lifecycle["reasoning_stream_size"] <= 8


if __name__ == "__main__":
    test_gui_runtime_snapshot_includes_active_tribunal_lifecycle()
    print("test_runtime_snapshot_tribunal_lifecycle PASS")
