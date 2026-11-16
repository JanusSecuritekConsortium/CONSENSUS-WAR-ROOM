from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import AETERNUM, BELLATOR, RATIONALIS, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from ui.components.monolith_panel import build_monolith_panel
from ui.themes.catalog import THEMES


def _card_texts(panel, card_index: int) -> list:
    card = panel.controls[card_index + 1]
    text_column = card.content.controls[0]
    return text_column.controls


def test_monolith_cards_use_theme_specific_primary_titles() -> None:
    statuses = {key: "ONLINE" for key in TRIBUNAL_AGENT_IDS}
    for theme in THEMES.values():
        panel = build_monolith_panel(theme, DEFAULT_NODES, statuses)
        for index, key in enumerate(TRIBUNAL_AGENT_IDS):
            controls = _card_texts(panel, index)

            assert controls[0].value == theme.monolith_labels[key]["node"]
            assert controls[1].value == key
            assert controls[2].value == theme.monolith_labels[key]["core"]
            assert controls[0].size > controls[1].size


def test_global_monolith_display_order_is_bellator_aeternum_rationalis() -> None:
    assert TRIBUNAL_AGENT_IDS == (BELLATOR, AETERNUM, RATIONALIS)

    panel = build_monolith_panel(THEMES["military"], DEFAULT_NODES, {key: "ONLINE" for key in TRIBUNAL_AGENT_IDS})
    displayed_ids = [_card_texts(panel, index)[1].value for index in range(3)]

    assert displayed_ids == [BELLATOR, AETERNUM, RATIONALIS]


def test_arbiter_falls_back_to_canonical_control_core() -> None:
    panel = build_monolith_panel(THEMES["eva"], DEFAULT_NODES, {"ARBITER": "DEGRADED"})
    controls = _card_texts(panel, 3)

    assert controls[0].value == "ARBITER"
    assert controls[1].value == "ARBITER"
    assert controls[2].value == "CONTROL CORE"


if __name__ == "__main__":
    test_monolith_cards_use_theme_specific_primary_titles()
    test_global_monolith_display_order_is_bellator_aeternum_rationalis()
    test_arbiter_falls_back_to_canonical_control_core()
    print("test_gui_monolith_naming PASS")


def test_cards_show_the_real_model_its_memory_state_and_settings() -> None:
    from config.names import ARBITER, RATIONALIS
    resolved = {RATIONALIS: "unsloth/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_M.gguf",
                ARBITER: "NousResearch/Hermes-3-Llama-3.1-8B-GGUF/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"}
    states = {resolved[RATIONALIS]: "loaded", resolved[ARBITER]: "unloaded"}
    panel = build_monolith_panel(THEMES["military"], DEFAULT_NODES, {}, resolved_models=resolved, model_states=states)
    rationalis = [c.value for c in _card_texts(panel, 2)]
    assert "Qwen3.8-27B Q4_K_M" in rationalis
    node = DEFAULT_NODES[RATIONALIS]
    assert f"IN MEMORY | T {node.temperature:g} | MAX {node.max_output_tokens} TOK" in rationalis
    arbiter = [c.value for c in _card_texts(panel, 3)]
    assert "Hermes-3-Llama-3.1-8B Q4_K_M" in arbiter and "ON DISK | VERDICT BY RULES" in arbiter
    assert not any("LATENCY" in str(value) for value in rationalis + arbiter)  # no invented numbers


def test_card_says_dash_when_the_server_has_not_answered() -> None:
    panel = build_monolith_panel(THEMES["military"], DEFAULT_NODES, {})
    assert any(str(c.value).startswith("-- | T ") for c in _card_texts(panel, 0))


def test_model_states_refresh_in_the_background_and_never_block() -> None:
    from ui import model_states
    model_states.reset({"old": "loaded"})
    started = []

    class Thread:
        def __init__(self, target, daemon):
            self.target = target

        def start(self):
            started.append(self.target)

    assert model_states.load_states("http://x", now=100.0, fetch=lambda url: {"new": "loading"}, start=Thread) == {"old": "loaded"}
    started[0]()  # the background check finishes
    assert model_states.load_states("http://x", now=101.0, start=Thread) == {"new": "loading"}
    assert len(started) == 1  # no new check within REFRESH_SECONDS
    assert model_states.memory_label("missing-model-name", {"new": "loading"}) == "MISSING"
    model_states.reset()
