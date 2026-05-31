from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.simulation.store import create_stored_scenario, expand_stored_branch


def test_branch_expansion_requires_and_preserves_operator_assumptions() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "simulation.jsonl"
        scenario = create_stored_scenario(title="Deterministic", description="No forecast", scenario_type="strategic_forecast", path=path)
        root = scenario.generated_branches[0]
        assumptions = {"fuel_price": "operator_supplied_high"}
        branch = expand_stored_branch(scenario.scenario_id, root.branch_id, assumptions_delta=assumptions, path=path)
        assert branch.assumptions_delta == assumptions
        assert branch.assumptions_used == assumptions
        assert branch.summary == "Deterministic branch derived from operator-provided assumptions."

        try:
            expand_stored_branch(scenario.scenario_id, root.branch_id, assumptions_delta={}, path=path)
        except ValueError as exc:
            assert "operator-provided assumptions" in str(exc)
        else:
            raise AssertionError("empty branch assumptions should fail")


if __name__ == "__main__":
    test_branch_expansion_requires_and_preserves_operator_assumptions()
    print("test_branch_expansion_deterministic PASS")
