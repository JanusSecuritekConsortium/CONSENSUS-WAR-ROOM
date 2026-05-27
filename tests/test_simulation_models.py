from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.simulation.scenarios import create_scenario


def test_scenario_model_contains_canonical_fields() -> None:
    scenario = create_scenario(
        title="Architecture only",
        description="No forecast output.",
        scenario_type="strategic_forecast",
        proposal_id="prop_1",
    )
    payload = scenario.to_dict()
    assert payload["scenario_id"].startswith("sim_")
    assert payload["proposal_id"] == "prop_1"
    assert payload["scenario_type"] == "strategic_forecast"
    assert payload["generated_branches"][0]["parent_branch_id"] is None


if __name__ == "__main__":
    test_scenario_model_contains_canonical_fields()
    print("test_simulation_models PASS")
