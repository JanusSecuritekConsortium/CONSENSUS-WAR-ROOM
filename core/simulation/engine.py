from __future__ import annotations

from core.simulation.branches import generate_child_branch
from core.simulation.models import Branch, Scenario
from core.simulation.scenarios import create_scenario


class SimulationEngine:
    status = "READY"
    mode = "deterministic_scaffold"

    def create_scenario(self, **kwargs) -> Scenario:
        return create_scenario(**kwargs)

    def expand_once(self, scenario: Scenario, parent: Branch | None = None) -> Branch:
        source = parent or scenario.generated_branches[0]
        return generate_child_branch(
            source,
            assumptions_delta={"branch_depth": source.divergence_index + 1},
            summary="Deterministic architecture branch; no autonomous forecast generated.",
        )
