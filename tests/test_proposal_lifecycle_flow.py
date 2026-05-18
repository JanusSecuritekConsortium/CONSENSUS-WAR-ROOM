from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import create_gui_state, submit_proposal_live_for_gui
from ui.war_room_runtime import proposal_lifecycle_events


def test_proposal_lifecycle_flow_has_expected_milestones() -> None:
    flow = proposal_lifecycle_events()

    assert flow == (
        "PROPOSAL RECEIVED",
        "MONOLITH ACTIVATION",
        "VOTE SYNCHRONIZATION",
        "ARBITER SYNCHRONIZATION",
        "CONSENSUS LOCKED",
    )


def test_gui_submission_records_timeline_and_lock() -> None:
    state = create_gui_state("MILITARY", RuntimeConfig(theme="military", backend="mock"))

    result = submit_proposal_live_for_gui(
        state,
        "Approve a proposal lifecycle visualization test.",
        skip_animations=True,
    )

    rendered_timeline = "\n".join(state.timeline_events)
    assert "PROPOSAL" in rendered_timeline
    assert "vote" in rendered_timeline.lower()
    assert "consensus locked" in rendered_timeline.lower()
    assert state.consensus_locked is True
    assert state.current_result is result


if __name__ == "__main__":
    test_proposal_lifecycle_flow_has_expected_milestones()
    test_gui_submission_records_timeline_and_lock()
    print("test_proposal_lifecycle_flow PASS")
