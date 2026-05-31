from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import make_gui_state
from ui.flet_app import build_simulation_viewer


def _flatten_text(control) -> str:
    values: list[str] = []
    for attribute in ("value", "text"):
        value = getattr(control, attribute, None)
        if isinstance(value, str):
            values.append(value)
    content = getattr(control, "content", None)
    if content is not None:
        values.append(_flatten_text(content))
    for child in getattr(control, "controls", []) or []:
        values.append(_flatten_text(child))
    return "\n".join(values)


def test_simulation_history_overlay_has_tree_and_export_actions() -> None:
    state = make_gui_state("janus")
    rendered = _flatten_text(
        build_simulation_viewer(
            state,
            scenarios=[{"scenario_id": "sim_1", "title": "Operator Scenario", "scenario_type": "strategic_forecast", "status": "DRAFT"}],
        )
    )
    assert "SIMULATION REGISTRY" in rendered
    assert "OPEN TREE" in rendered
    assert "EXPORT DOSSIER" in rendered


if __name__ == "__main__":
    test_simulation_history_overlay_has_tree_and_export_actions()
    print("test_simulation_history_overlay PASS")
