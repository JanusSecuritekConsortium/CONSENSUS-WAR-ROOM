from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import make_gui_state
from ui.flet_app import COMMAND_PALETTE_ACTIONS, build_simulation_viewer, execute_command_palette_action


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "text") and isinstance(control.text, str):
        values.append(control.text)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def test_gui_simulation_actions_are_registered_and_overlay_renders() -> None:
    assert "Create Simulation" in COMMAND_PALETTE_ACTIONS
    assert "View Simulations" in COMMAND_PALETTE_ACTIONS
    assert "Export Simulation Dossier" in COMMAND_PALETTE_ACTIONS
    state = make_gui_state("eva")
    execute_command_palette_action(state, "View Simulations")
    assert state.simulation_viewer_open is True
    text = "\n".join(_flatten_text(build_simulation_viewer(state, scenarios=[])))
    assert "SIMULATION REGISTRY" in text


if __name__ == "__main__":
    test_gui_simulation_actions_are_registered_and_overlay_renders()
    print("test_gui_simulation_actions PASS")
