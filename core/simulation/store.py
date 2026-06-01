from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.paths import SYSTEM_ROOT
from core.simulation.branches import generate_child_branch
from core.simulation.models import Branch, Scenario, utc_now
from core.simulation.scenarios import create_scenario


SIMULATION_HISTORY_PATH = SYSTEM_ROOT / "reports" / "simulation_history.jsonl"


def _append_record(record: Dict[str, Any], path: Path = SIMULATION_HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")


def _read_records(path: Path = SIMULATION_HISTORY_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def create_stored_scenario(*, path: Path = SIMULATION_HISTORY_PATH, **kwargs: Any) -> Scenario:
    scenario = create_scenario(**kwargs)
    _append_record({"record_type": "scenario", **scenario.to_dict()}, path)
    for branch in scenario.generated_branches:
        _append_record({"record_type": "branch", "scenario_id": scenario.scenario_id, **branch.to_dict()}, path)
    return scenario


def append_branch(scenario_id: str, branch: Branch, *, path: Path = SIMULATION_HISTORY_PATH) -> Branch:
    _append_record({"record_type": "branch", "scenario_id": scenario_id, **branch.to_dict()}, path)
    return branch


def get_scenario(scenario_id: str, *, path: Path = SIMULATION_HISTORY_PATH) -> Dict[str, Any] | None:
    records = _read_records(path)
    scenarios = [
        record
        for record in records
        if record.get("record_type") == "scenario" and record.get("scenario_id") == scenario_id
    ]
    if not scenarios:
        return None
    scenario = dict(scenarios[-1])
    scenario["generated_branches"] = branches_for_scenario(scenario_id, path=path)
    return scenario


def expand_stored_branch(
    scenario_id: str,
    parent_branch_id: str,
    *,
    assumptions_delta: Dict[str, Any],
    escalation_flags: List[str] | None = None,
    title: str = "Operator Assumption Branch",
    summary: str = "Deterministic branch derived from operator-provided assumptions.",
    path: Path = SIMULATION_HISTORY_PATH,
) -> Branch:
    if not assumptions_delta:
        raise ValueError("Branch expansion requires operator-provided assumptions.")
    records = branches_for_scenario(scenario_id, path=path)
    parent_record = next((record for record in records if record.get("branch_id") == parent_branch_id), None)
    if parent_record is None:
        raise KeyError(f"Unknown branch: {parent_branch_id}")
    parent = _branch_from_record(parent_record)
    branch = generate_child_branch(
        parent,
        assumptions_delta=assumptions_delta,
        escalation_flags=escalation_flags,
        title=title,
        summary=summary,
    )
    return append_branch(scenario_id, branch, path=path)


def list_recent_scenarios(limit: int = 20, *, path: Path = SIMULATION_HISTORY_PATH) -> List[Dict[str, Any]]:
    scenarios = [record for record in _read_records(path) if record.get("record_type") == "scenario"]
    scenarios.sort(key=lambda record: str(record.get("created_at", "")), reverse=True)
    return scenarios[:limit]


def branches_for_scenario(scenario_id: str, *, path: Path = SIMULATION_HISTORY_PATH) -> List[Dict[str, Any]]:
    return [
        record
        for record in _read_records(path)
        if record.get("record_type") == "branch" and record.get("scenario_id") == scenario_id
    ]


def get_simulation_status(path: Path = SIMULATION_HISTORY_PATH) -> Dict[str, Any]:
    records = _read_records(path)
    scenarios = [record for record in records if record.get("record_type") == "scenario"]
    branches = [record for record in records if record.get("record_type") == "branch"]
    latest = max(scenarios, key=lambda record: str(record.get("created_at", ""))) if scenarios else None
    latest_branch_count = len(branches_for_scenario(str(latest.get("scenario_id")), path=path)) if latest else 0
    return {
        "history_path": str(path),
        "engine_status": "READY",
        "scenario_count": len(scenarios),
        "branch_count": len(branches),
        "latest_simulation_id": latest.get("scenario_id") if latest else None,
        "latest_branch_count": latest_branch_count,
        "latest_simulation_dossier": _latest_simulation_dossier(),
    }


def _branch_from_record(record: Dict[str, Any]) -> Branch:
    return Branch(
        branch_id=str(record.get("branch_id")),
        parent_branch_id=record.get("parent_branch_id") or record.get("parent_id"),
        scenario_id=str(record.get("scenario_id")),
        depth=int(record.get("depth", record.get("divergence_index", 0)) or 0),
        title=str(record.get("title") or "Operator Assumption Branch"),
        probability=float(record.get("probability", 0.0) or 0.0),
        risk_score=float(record.get("risk_score", 0.0) or 0.0),
        summary=str(record.get("summary") or ""),
        assumptions_delta=dict(record.get("assumptions_delta") or {}),
        assumptions_used=dict(record.get("assumptions_used") or {}),
        escalation_flags=list(record.get("escalation_flags") or []),
        tribunal_votes=dict(record.get("tribunal_votes") or {}),
        generated_at=str(record.get("generated_at") or utc_now()),
        divergence_index=int(record.get("divergence_index", record.get("depth", 0)) or 0),
    )


def _latest_simulation_dossier() -> str | None:
    dossier_dir = SYSTEM_ROOT / "reports" / "simulation_dossiers"
    candidates = list(dossier_dir.glob("*_simulation_dossier.json"))
    if not candidates:
        return None
    return str(max(candidates, key=lambda item: item.stat().st_mtime))


__all__ = [
    "SIMULATION_HISTORY_PATH",
    "append_branch",
    "branches_for_scenario",
    "create_stored_scenario",
    "expand_stored_branch",
    "get_scenario",
    "get_simulation_status",
    "list_recent_scenarios",
]
