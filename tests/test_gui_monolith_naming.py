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


def test_arbiter_falls_back_to_canonical_control_core() -> None:
    panel = build_monolith_panel(THEMES["eva"], DEFAULT_NODES, {"ARBITER": "DEGRADED"})
    controls = _card_texts(panel, 3)

    assert controls[0].value == "ARBITER"
    assert controls[1].value == "ARBITER"
    assert controls[2].value == "CONTROL CORE"


if __name__ == "__main__":
    test_monolith_cards_use_theme_specific_primary_titles()
    test_arbiter_falls_back_to_canonical_control_core()
    print("test_gui_monolith_naming PASS")
