from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from config.runtime import RuntimeConfig
from ui.flet_app import advance_war_room_activity, create_gui_state
from ui.war_room_runtime import MONOLITH_ACTIVITY_STATES, transition_state


def test_monolith_state_machine_accepts_expected_states() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))

    for activity_state in MONOLITH_ACTIVITY_STATES:
        transition_state(state.monolith_activity_states, TRIBUNAL_AGENT_IDS[0], activity_state, state.timeline_events)
        assert state.monolith_activity_states[TRIBUNAL_AGENT_IDS[0]] == activity_state


def test_war_room_activity_ticks_without_provider_probe() -> None:
    state = create_gui_state("JANUS", RuntimeConfig(theme="janus", backend="mock"))
    previous_index = state.pulse_index

    advance_war_room_activity(state)

    assert state.pulse_index == previous_index + 1
    assert set([*TRIBUNAL_AGENT_IDS, ARBITER]) <= set(state.monolith_latencies_ms)
    assert state.heartbeat_text


if __name__ == "__main__":
    test_monolith_state_machine_accepts_expected_states()
    test_war_room_activity_ticks_without_provider_probe()
    print("test_war_room_state_machine PASS")
