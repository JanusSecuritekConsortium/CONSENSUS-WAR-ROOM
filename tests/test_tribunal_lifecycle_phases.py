from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from core.tribunal_events import TRIBUNAL_PHASES, convergence_percent, phase_for_verdict
from ui.flet_app import create_gui_state, submit_proposal_live_for_gui


def test_live_submission_records_explicit_tribunal_phases() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    result = submit_proposal_live_for_gui(
        state,
        "Approve explicit lifecycle phase coverage.",
        skip_animations=True,
    )
    phases = [str(event["phase"]) for event in state.lifecycle_events]

    assert "CLASSIFYING" in phases
    assert "DISPATCHING" in phases
    assert "ANALYZING" in phases
    assert "DELIBERATING" in phases
    assert "SYNTHESIZING" in phases
    assert phase_for_verdict(result.verdict, result.terminal_branch, result.review_triggers) in phases
    assert state.lifecycle_state == "EXPORT_READY"
    assert set(phases) <= set(TRIBUNAL_PHASES)


def test_phase_durations_and_convergence_are_bounded_values() -> None:
    state = create_gui_state("JANUS", RuntimeConfig(theme="janus", backend="mock"))
    submit_proposal_live_for_gui(state, "Approve convergence lifecycle coverage.", skip_animations=True)

    assert state.phase_durations
    assert 0.0 <= state.convergence_percent <= 1.0
    assert state.convergence_percent == convergence_percent({k: v for k, v in state.current_result.votes.items()})


if __name__ == "__main__":
    test_live_submission_records_explicit_tribunal_phases()
    test_phase_durations_and_convergence_are_bounded_values()
    print("test_tribunal_lifecycle_phases PASS")
