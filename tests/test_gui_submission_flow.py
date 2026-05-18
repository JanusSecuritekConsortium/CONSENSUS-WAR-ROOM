from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from core.models import TribunalResult
from ui.flet_app import create_gui_state, submit_proposal_for_gui


def test_gui_mock_submission_flows_through_tribunal() -> None:
    state = create_gui_state("JANUS", RuntimeConfig(theme="janus", backend="mock"))
    result = submit_proposal_for_gui(state, "Approve a mock GUI integration smoke proposal.")

    assert isinstance(result, TribunalResult)
    assert state.current_result is result
    assert state.current_proposal
    assert result.theme == "janus"
    assert result.votes
    assert state.recent_decisions


if __name__ == "__main__":
    test_gui_mock_submission_flows_through_tribunal()
    print("test_gui_submission_flow PASS")
