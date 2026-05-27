from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import make_gui_state
from ui.flet_app import runtime_snapshot_from_gui_state


def test_runtime_snapshot_includes_proposal_history_and_verdict_export() -> None:
    snapshot = runtime_snapshot_from_gui_state(make_gui_state("eva"))
    assert "proposal_history_status" in snapshot
    assert "history_path" in snapshot["proposal_history_status"]
    assert "latest_verdict_export" in snapshot


if __name__ == "__main__":
    test_runtime_snapshot_includes_proposal_history_and_verdict_export()
    print("test_runtime_snapshot_proposal_history PASS")
