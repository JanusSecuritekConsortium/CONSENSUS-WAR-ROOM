from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.simulation import store
from tests.helpers.gui_harness import make_gui_state
from ui import flet_app


def _flatten_text(control) -> str:
    values = [str(value) for value in (getattr(control, "value", None), getattr(control, "text", None)) if isinstance(value, str)]
    if getattr(control, "content", None) is not None:
        values.append(_flatten_text(control.content))
    for child in getattr(control, "controls", []) or []:
        values.append(_flatten_text(child))
    return "\n".join(values)


def test_branch_tree_viewer_lists_stored_root_branch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "simulation.jsonl"
        scenario = store.create_stored_scenario(title="Tree", description="Operator only", scenario_type="strategic_forecast", path=path)
        original = flet_app.get_scenario
        try:
            flet_app.get_scenario = lambda scenario_id: store.get_scenario(scenario_id, path=path)
            state = make_gui_state("military")
            state.selected_simulation_id = scenario.scenario_id
            rendered = _flatten_text(flet_app.build_branch_tree_viewer(state))
            assert "BRANCH TREE" in rendered
            assert scenario.generated_branches[0].branch_id in rendered
            assert "EXPAND WITH OPERATOR ASSUMPTIONS" in rendered
        finally:
            flet_app.get_scenario = original


if __name__ == "__main__":
    test_branch_tree_viewer_lists_stored_root_branch()
    print("test_branch_tree_viewer PASS")
