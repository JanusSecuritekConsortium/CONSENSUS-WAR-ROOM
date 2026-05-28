from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Branch:
    branch_id: str
    parent_branch_id: str | None
    probability: float
    risk_score: float
    summary: str
    assumptions_delta: Dict[str, Any] = field(default_factory=dict)
    escalation_flags: List[str] = field(default_factory=list)
    tribunal_votes: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=utc_now)
    divergence_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    created_at: str
    proposal_id: str | None
    title: str
    description: str
    scenario_type: str
    assumptions: Dict[str, Any]
    actors: List[str]
    triggers: List[str]
    timeline_horizon: str
    branch_depth: int
    confidence_model: str
    generated_branches: List[Branch] = field(default_factory=list)
    status: str = "DRAFT"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["generated_branches"] = [branch.to_dict() if isinstance(branch, Branch) else branch for branch in self.generated_branches]
        return payload


@dataclass(frozen=True)
class SimulationEvaluation:
    scenario_id: str
    branch_id: str
    tribunal_votes: Dict[str, Any]
    evaluated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
