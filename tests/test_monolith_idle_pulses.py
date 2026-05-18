from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import TRIBUNAL_AGENT_IDS
from ui.war_room_runtime import build_runtime_details, default_activity_states, default_latencies, idle_activity_text, pulse_frame


def test_idle_pulse_frames_cycle_without_layout_shift() -> None:
    frames = [pulse_frame(index) for index in range(8)]

    assert set(frames) == {"░", "▒", "▓"}
    assert len({len(frame) for frame in frames}) == 1


def test_runtime_details_include_latency_and_activity_text() -> None:
    states = default_activity_states()
    latencies = default_latencies(2)
    details = build_runtime_details(states, latencies, 2)

    for agent_id in TRIBUNAL_AGENT_IDS:
        assert details[agent_id]["state"] == "IDLE"
        assert "AWAITING PROPOSAL" in str(details[agent_id]["activity"])
        assert int(details[agent_id]["latency_ms"]) > 0
        assert details[agent_id]["signal"]


def test_idle_activity_text_cycles_dots() -> None:
    assert {idle_activity_text(index) for index in range(3)} == {
        "AWAITING PROPOSAL.",
        "AWAITING PROPOSAL..",
        "AWAITING PROPOSAL...",
    }


if __name__ == "__main__":
    test_idle_pulse_frames_cycle_without_layout_shift()
    test_runtime_details_include_latency_and_activity_text()
    test_idle_activity_text_cycles_dots()
    print("test_monolith_idle_pulses PASS")
