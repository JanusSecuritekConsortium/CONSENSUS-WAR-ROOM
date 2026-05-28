from __future__ import annotations

import uuid
from typing import Any, Dict, List

from core.simulation.branches import create_initial_branch
from core.simulation.models import Scenario, utc_now
from core.simulation.registry import default_registry


def create_scenario(
    *,
    title: str,
    description: str,
    scenario_type: str,
    proposal_id: str | None = None,
    assumptions: Dict[str, Any] | None = None,
    actors: List[str] | None = None,
    triggers: List[str] | None = None,
    timeline_horizon: str = "unspecified",
    branch_depth: int = 1,
    confidence_model: str | None = None,
    status: str = "DRAFT",
) -> Scenario:
    registry = default_registry()
    definition = registry.get(scenario_type)
    scenario_id = f"sim_{uuid.uuid4().hex[:12]}"
    initial_branch = create_initial_branch(scenario_id, "Baseline branch awaiting tribunal evaluation.")
    return Scenario(
        scenario_id=scenario_id,
        created_at=utc_now(),
        proposal_id=proposal_id,
        title=title.strip() or definition.title,
        description=description.strip(),
        scenario_type=scenario_type,
        assumptions=assumptions or {},
        actors=actors or [],
        triggers=triggers or [],
        timeline_horizon=timeline_horizon,
        branch_depth=max(0, int(branch_depth)),
        confidence_model=confidence_model or definition.default_confidence_model,
        generated_branches=[initial_branch],
        status=status,
    )
