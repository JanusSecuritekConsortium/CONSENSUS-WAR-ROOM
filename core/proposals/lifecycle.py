from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from core.export.verdict import export_latest_verdict
from core.proposals.store import (
    PROPOSAL_HISTORY_PATH,
    get_proposal,
    lifecycle_counts,
    list_recent_proposals,
    update_proposal,
)


def decision_status_from_trace(trace: Dict[str, Any] | None) -> str:
    if not isinstance(trace, dict) or trace.get("error"):
        return "ERROR"
    final_verdict = str(trace.get("final_verdict") or trace.get("verdict") or "").upper()
    terminal_branch = str(trace.get("terminal_branch") or "").lower()
    if "escalat" in final_verdict.lower() or "escalat" in terminal_branch:
        return "ESCALATED"
    if final_verdict == "NO_CONSENSUS" or "no_consensus" in terminal_branch or "classification_failure" in terminal_branch:
        return "NO_CONSENSUS"
    if final_verdict:
        return "DECIDED"
    return "ERROR"


def _trace_id(trace: Dict[str, Any]) -> str | None:
    value = trace.get("proposal_id") or trace.get("session_id")
    return str(value) if value else None


def _find_proposal_for_trace(trace: Dict[str, Any], path: Path) -> str | None:
    trace_id = _trace_id(trace)
    if not trace_id:
        return None
    direct = get_proposal(trace_id, path=path)
    if direct is not None:
        return str(direct["proposal_id"])
    for proposal in list_recent_proposals(limit=5000, include_archived=True, path=path):
        if str(proposal.get("linked_decision_trace_id") or "") == trace_id:
            return str(proposal["proposal_id"])
    return None


def update_proposal_decision_status(
    proposal_id: str,
    decision_status: str,
    *,
    decision_timestamp: str | None = None,
    path: Path = PROPOSAL_HISTORY_PATH,
) -> Dict[str, Any]:
    return update_proposal(
        proposal_id,
        path=path,
        decision_status=decision_status,
        decision_timestamp=decision_timestamp,
    )


def attach_verdict_exports(
    proposal_id: str,
    verdict_exports: Dict[str, Any],
    *,
    path: Path = PROPOSAL_HISTORY_PATH,
) -> Dict[str, Any]:
    json_path = verdict_exports.get("json_path")
    markdown_path = verdict_exports.get("markdown_path")
    return update_proposal(
        proposal_id,
        path=path,
        linked_verdict_path=markdown_path or json_path,
        linked_verdict_export_json=json_path,
        linked_verdict_export_md=markdown_path,
    )


def link_decision_trace_to_proposal(
    trace: Dict[str, Any] | None,
    *,
    proposal_id: str | None = None,
    export_verdict: bool = True,
    path: Path = PROPOSAL_HISTORY_PATH,
) -> Dict[str, Any]:
    if not isinstance(trace, dict) or not trace:
        return {"linked": False, "reason": "missing_trace", "proposal_id": proposal_id}
    target_proposal_id = proposal_id or _find_proposal_for_trace(trace, path)
    if not target_proposal_id:
        return {"linked": False, "reason": "proposal_not_found", "trace_id": _trace_id(trace)}
    decision_status = decision_status_from_trace(trace)
    updated = update_proposal(
        target_proposal_id,
        path=path,
        linked_decision_trace_id=_trace_id(trace),
        decision_status=decision_status,
        decision_timestamp=trace.get("timestamp"),
    )
    verdict_exports: Dict[str, Any] | None = None
    if export_verdict:
        verdict_exports = export_latest_verdict(trace)
        updated = attach_verdict_exports(target_proposal_id, verdict_exports, path=path)
    return {
        "linked": True,
        "proposal_id": target_proposal_id,
        "decision_status": decision_status,
        "trace_id": _trace_id(trace),
        "verdict_exports": verdict_exports,
        "proposal": updated,
    }


def get_proposal_decision_summary(proposal_id: str, *, path: Path = PROPOSAL_HISTORY_PATH) -> Dict[str, Any]:
    proposal = get_proposal(proposal_id, path=path)
    if proposal is None:
        return {"proposal_id": proposal_id, "found": False}
    return {
        "proposal_id": proposal_id,
        "found": True,
        "title": proposal.get("title"),
        "status": proposal.get("status"),
        "decision_status": proposal.get("decision_status") or proposal.get("status"),
        "decision_timestamp": proposal.get("decision_timestamp"),
        "linked_decision_trace_id": proposal.get("linked_decision_trace_id"),
        "linked_verdict_export_json": proposal.get("linked_verdict_export_json"),
        "linked_verdict_export_md": proposal.get("linked_verdict_export_md"),
    }


def proposal_lifecycle_summary(path: Path = PROPOSAL_HISTORY_PATH) -> Dict[str, Any]:
    counts = lifecycle_counts(path)
    return {
        "history_path": str(path),
        "counts": counts,
        "decided_total": counts.get("DECIDED", 0),
        "no_consensus_total": counts.get("NO_CONSENSUS", 0),
        "escalated_total": counts.get("ESCALATED", 0),
        "error_total": counts.get("ERROR", 0),
    }


__all__ = [
    "attach_verdict_exports",
    "decision_status_from_trace",
    "get_proposal_decision_summary",
    "link_decision_trace_to_proposal",
    "proposal_lifecycle_summary",
    "update_proposal_decision_status",
]
