from __future__ import annotations

from core.simulation.branches import generate_child_branch
from core.simulation.models import Branch, Scenario
from core.simulation.scenarios import create_scenario


class SimulationEngine:
    status = "READY"
    mode = "deterministic_scaffold"

    def create_scenario(self, **kwargs) -> Scenario:
        return create_scenario(**kwargs)

    def expand_once(
        self,
        scenario: Scenario,
        parent: Branch | None = None,
        *,
        assumptions_delta: dict | None = None,
        escalation_flags: list[str] | None = None,
        title: str = "Operator Assumption Branch",
        summary: str = "Deterministic branch derived from operator-provided assumptions.",
    ) -> Branch:
        source = parent or scenario.generated_branches[0]
        if not assumptions_delta:
            raise ValueError("Branch expansion requires operator-provided assumptions.")
        return generate_child_branch(
            source,
            assumptions_delta=assumptions_delta,
            escalation_flags=escalation_flags,
            title=title,
            summary=summary,
        )
