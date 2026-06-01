from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from core.paths import SYSTEM_ROOT
from core.simulation.store import SIMULATION_HISTORY_PATH, get_scenario


SIMULATION_DOSSIER_DIR = SYSTEM_ROOT / "reports" / "simulation_dossiers"


def export_simulation_dossier(
    scenario_id: str,
    *,
    output_dir: Path = SIMULATION_DOSSIER_DIR,
    history_path: Path = SIMULATION_HISTORY_PATH,
) -> Dict[str, str]:
    scenario = get_scenario(scenario_id, path=history_path)
    if scenario is None:
        raise KeyError(f"Unknown simulation scenario: {scenario_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "exported_at": timestamp,
        "simulation_mode": "deterministic_operator_scaffold",
        "forecast_disclaimer": "No autonomous forecast or invented intelligence is included.",
        "scenario": scenario,
        "branches": scenario.get("generated_branches", []),
        "source_history_path": str(history_path),
    }
    json_path = output_dir / f"{scenario_id}_simulation_dossier.json"
    markdown_path = output_dir / f"{scenario_id}_simulation_dossier.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path)}


def latest_simulation_dossier_status(output_dir: Path = SIMULATION_DOSSIER_DIR) -> Dict[str, str | None]:
    json_files = list(output_dir.glob("*_simulation_dossier.json"))
    md_files = list(output_dir.glob("*_simulation_dossier.md"))
    return {
        "path": str(output_dir),
        "latest_json": str(max(json_files, key=lambda item: item.stat().st_mtime)) if json_files else None,
        "latest_markdown": str(max(md_files, key=lambda item: item.stat().st_mtime)) if md_files else None,
    }


def _render_markdown(payload: Dict[str, Any]) -> str:
    scenario = payload["scenario"]
    branches = payload["branches"]
    lines = [
        f"# Simulation Dossier: {scenario.get('title') or scenario.get('scenario_id')}",
        "",
        f"- Scenario ID: `{scenario.get('scenario_id')}`",
        f"- Type: `{scenario.get('scenario_type')}`",
        f"- Status: `{scenario.get('status')}`",
        f"- Linked Proposal: `{scenario.get('proposal_id') or '--'}`",
        f"- Horizon: `{scenario.get('timeline_horizon') or scenario.get('horizon') or '--'}`",
        f"- Created: `{scenario.get('created_at')}`",
        f"- Updated: `{scenario.get('updated_at')}`",
        "",
        "## Scope",
        "",
        str(scenario.get("description") or "No description supplied."),
        "",
        "## Operator Inputs",
        "",
        f"- Actors: {', '.join(scenario.get('actors') or []) or '--'}",
        f"- Triggers: {', '.join(scenario.get('triggers') or []) or '--'}",
        f"- Assumptions: `{json.dumps(scenario.get('assumptions') or {}, sort_keys=True)}`",
        "",
        "## Branch Tree",
        "",
    ]
    for branch in branches:
        lines.extend(
            [
                f"### {branch.get('title') or branch.get('branch_id')}",
                "",
                f"- Branch ID: `{branch.get('branch_id')}`",
                f"- Parent: `{branch.get('parent_id') or branch.get('parent_branch_id') or '--'}`",
                f"- Depth: `{branch.get('depth', 0)}`",
                f"- Probability scaffold: `{branch.get('probability')}`",
                f"- Risk scaffold: `{branch.get('risk_score')}`",
                f"- Escalation flags: {', '.join(branch.get('escalation_flags') or []) or '--'}",
                f"- Assumptions used: `{json.dumps(branch.get('assumptions_used') or {}, sort_keys=True)}`",
                "",
                str(branch.get("summary") or ""),
                "",
            ]
        )
    lines.extend(
        [
            "## Deterministic Scaffold Notice",
            "",
            "This dossier contains operator-provided assumptions and deterministic branch bookkeeping only. It does not contain autonomous forecasts or invented intelligence.",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = ["SIMULATION_DOSSIER_DIR", "export_simulation_dossier", "latest_simulation_dossier_status"]
