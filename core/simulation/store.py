from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.paths import SYSTEM_ROOT
from core.simulation.models import Branch, Scenario
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
    }


__all__ = [
    "SIMULATION_HISTORY_PATH",
    "append_branch",
    "branches_for_scenario",
    "create_stored_scenario",
    "get_simulation_status",
    "list_recent_scenarios",
]
