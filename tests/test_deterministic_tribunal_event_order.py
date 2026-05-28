from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import create_gui_state, submit_proposal_live_for_gui


def test_tribunal_phase_order_is_deterministic() -> None:
    state = create_gui_state("military", RuntimeConfig(theme="military", backend="mock"))
    submit_proposal_live_for_gui(state, "Approve deterministic phase ordering.", skip_animations=True)
    phases = [str(event["phase"]) for event in state.lifecycle_events]

    expected_prefix = ["CLASSIFYING", "DISPATCHING", "ANALYZING", "DELIBERATING", "SYNTHESIZING"]
    assert phases[:5] == expected_prefix
    assert phases[-1] == "EXPORT_READY"
    assert len(phases) <= 32


if __name__ == "__main__":
    test_tribunal_phase_order_is_deterministic()
    print("test_deterministic_tribunal_event_order PASS")
