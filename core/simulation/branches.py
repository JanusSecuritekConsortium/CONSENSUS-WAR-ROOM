from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from core.simulation.models import Branch


def _stable_suffix(*parts: Any) -> str:
    text = "|".join(str(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def evaluate_branch_probability(assumptions_delta: Dict[str, Any] | None = None, depth: int = 0) -> float:
    delta_size = len(assumptions_delta or {})
    return round(_clamp(0.65 - (depth * 0.08) - (delta_size * 0.03)), 4)


def score_branch_risk(escalation_flags: List[str] | None = None, assumptions_delta: Dict[str, Any] | None = None) -> float:
    flags = escalation_flags or []
    delta_size = len(assumptions_delta or {})
    return round(_clamp(0.2 + (len(flags) * 0.18) + (delta_size * 0.05)), 4)


def create_initial_branch(scenario_id: str, summary: str = "Baseline deterministic branch.") -> Branch:
    return Branch(
        branch_id=f"branch_{_stable_suffix(scenario_id, 'root')}",
        parent_branch_id=None,
        probability=evaluate_branch_probability(depth=0),
        risk_score=score_branch_risk(),
        summary=summary,
        divergence_index=0,
    )


def generate_child_branch(
    parent: Branch,
    *,
    assumptions_delta: Dict[str, Any] | None = None,
    escalation_flags: List[str] | None = None,
    summary: str = "Deterministic child branch scaffold.",
) -> Branch:
    delta = assumptions_delta or {}
    flags = escalation_flags or []
    divergence_index = parent.divergence_index + 1
    return Branch(
        branch_id=f"branch_{_stable_suffix(parent.branch_id, delta, flags, divergence_index)}",
        parent_branch_id=parent.branch_id,
        probability=evaluate_branch_probability(delta, divergence_index),
        risk_score=score_branch_risk(flags, delta),
        summary=summary,
        assumptions_delta=delta,
        escalation_flags=flags,
        divergence_index=divergence_index,
    )
