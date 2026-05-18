from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from ui.components.monolith_panel import build_monolith_panel
from ui.themes.catalog import THEMES
from ui.war_room_runtime import build_runtime_details, default_latencies


def test_monolith_runtime_details_use_distinct_glyphs_and_idle_phrases() -> None:
    states = {agent_id: "IDLE" for agent_id in TRIBUNAL_AGENT_IDS}
    details = build_runtime_details(states, default_latencies(0), 0)

    assert len({details[agent_id]["glyph"] for agent_id in TRIBUNAL_AGENT_IDS}) == len(TRIBUNAL_AGENT_IDS)
    assert "LOGIC" in str(details["RATIONALIS"]["activity"])
    assert "FORECAST" in str(details["AETERNUM"]["activity"])
    assert "TACTICAL" in str(details["BELLATOR"]["activity"])


def test_active_monolith_card_has_stronger_border() -> None:
    runtime_details = build_runtime_details(
        {"RATIONALIS": "VOTING", "AETERNUM": "IDLE", "BELLATOR": "IDLE", "ARBITER": "IDLE"},
        default_latencies(2),
        2,
    )
    panel = build_monolith_panel(
        THEMES["eva"],
        DEFAULT_NODES,
        {"RATIONALIS": "THINKING", "AETERNUM": "ONLINE", "BELLATOR": "ONLINE", "ARBITER": "ONLINE"},
        runtime_details=runtime_details,
    )
    rationalis_card = panel.controls[1]
    aeternum_card = panel.controls[2]

    assert rationalis_card.border.top.width == 2
    assert aeternum_card.border.top.width == 1


if __name__ == "__main__":
    test_monolith_runtime_details_use_distinct_glyphs_and_idle_phrases()
    test_active_monolith_card_has_stronger_border()
    print("test_monolith_identity_enhancement PASS")
