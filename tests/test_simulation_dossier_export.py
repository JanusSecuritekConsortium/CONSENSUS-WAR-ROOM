from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export.simulation import export_simulation_dossier
from core.simulation.store import create_stored_scenario, expand_stored_branch


def test_simulation_dossier_contains_operator_inputs_and_no_forecast_notice() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        history = root / "simulation.jsonl"
        scenario = create_stored_scenario(
            title="Export",
            description="Operator-defined test.",
            scenario_type="strategic_forecast",
            assumptions={"scope": "operator_defined"},
            actors=["Actor A"],
            triggers=["Trigger A"],
            path=history,
        )
        expand_stored_branch(scenario.scenario_id, scenario.generated_branches[0].branch_id, assumptions_delta={"delta": "operator_value"}, path=history)
        exported = export_simulation_dossier(scenario.scenario_id, output_dir=root / "dossiers", history_path=history)
        payload = json.loads(Path(exported["json_path"]).read_text(encoding="utf-8"))
        markdown = Path(exported["markdown_path"]).read_text(encoding="utf-8")
        assert payload["simulation_mode"] == "deterministic_operator_scaffold"
        assert payload["scenario"]["scenario_id"] == scenario.scenario_id
        assert len(payload["branches"]) == 2
        assert "does not contain autonomous forecasts or invented intelligence" in markdown


if __name__ == "__main__":
    test_simulation_dossier_contains_operator_inputs_and_no_forecast_notice()
    print("test_simulation_dossier_export PASS")
