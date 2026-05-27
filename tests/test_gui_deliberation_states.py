from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import TRIBUNAL_AGENT_IDS
from config.runtime import RuntimeConfig
from ui.flet_app import (
    LIFECYCLE_DELIBERATING,
    LIFECYCLE_PROPOSAL_RECEIVED,
    LIFECYCLE_SYNTHESIZING,
    LIFECYCLE_VERDICT_ISSUED,
    LIFECYCLE_VOTES_RECEIVED,
    create_gui_state,
    submit_proposal_live_for_gui,
)


def test_live_submission_moves_through_deliberation_states() -> None:
    state = create_gui_state("JANUS", RuntimeConfig(theme="janus", backend="mock"))
    seen_states: list[str] = []
    seen_statuses: list[dict[str, str]] = []

    def update() -> None:
        seen_states.append(state.lifecycle_state)
        seen_statuses.append(dict(state.monolith_statuses))

    result = submit_proposal_live_for_gui(
        state,
        "Approve a live GUI deliberation state test.",
        on_update=update,
        skip_animations=True,
    )

    assert LIFECYCLE_PROPOSAL_RECEIVED in seen_states
    assert LIFECYCLE_DELIBERATING in seen_states
    assert LIFECYCLE_VOTES_RECEIVED in seen_states
    assert LIFECYCLE_SYNTHESIZING in seen_states
    assert LIFECYCLE_VERDICT_ISSUED in seen_states
    assert state.current_result is result
    assert state.displayed_synthesis == result.reason
    assert state.displayed_confidence == result.confidence


def test_monoliths_think_then_receive_vote_details() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    snapshots: list[dict[str, str]] = []

    submit_proposal_live_for_gui(
        state,
        "Approve a monolith vote detail test.",
        on_update=lambda: snapshots.append(dict(state.monolith_statuses)),
        skip_animations=True,
    )

    assert any(all(snapshot.get(agent) == "THINKING" for agent in TRIBUNAL_AGENT_IDS) for snapshot in snapshots)
    assert set(TRIBUNAL_AGENT_IDS) <= set(state.monolith_vote_details)
    for agent in TRIBUNAL_AGENT_IDS:
        detail = state.monolith_vote_details[agent]
        assert detail["vote"] in {"APPROVE", "DENY", "ABSTAIN"}
        assert "evidence_quality" in detail
        assert "critical_risk" in detail
        assert isinstance(detail["reasoning"], str)
        assert float(detail["response_time"]) >= 0.0


if __name__ == "__main__":
    test_live_submission_moves_through_deliberation_states()
    test_monoliths_think_then_receive_vote_details()
    print("test_gui_deliberation_states PASS")
