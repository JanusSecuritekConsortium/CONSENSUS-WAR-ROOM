from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import make_gui_state
from ui.flet_app import build_simulation_create_overlay, execute_command_palette_action


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    for attribute in ("value", "text", "label"):
        value = getattr(control, attribute, None)
        if isinstance(value, str):
            values.append(value)
    content = getattr(control, "content", None)
    if content is not None:
        values.extend(_flatten_text(content))
    for child in getattr(control, "controls", []) or []:
        values.extend(_flatten_text(child))
    return values


def test_create_simulation_action_opens_operator_input_overlay() -> None:
    state = make_gui_state("eva")
    execute_command_palette_action(state, "Create Simulation")
    text = "\n".join(_flatten_text(build_simulation_create_overlay(state)))
    assert state.simulation_create_open is True
    assert "CREATE SIMULATION" in text
    assert "OPERATOR INPUTS ONLY" in text
    assert "ASSUMPTIONS" in text


if __name__ == "__main__":
    test_create_simulation_action_opens_operator_input_overlay()
    print("test_simulation_create_overlay PASS")
