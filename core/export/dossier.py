from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from config.version import SYSTEM_VERSION
from core.decision_trace import read_trace_by_proposal_id
from core.paths import SYSTEM_LOG_PATH, SYSTEM_ROOT
from core.proposals.store import PROPOSAL_HISTORY_PATH, get_proposal


DOSSIER_DIR = SYSTEM_ROOT / "reports" / "dossiers"


def _safe_id(value: Any) -> str:
    text = str(value or "unknown").strip() or "unknown"
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in text)[:96]


def _load_linked_verdict(proposal: Dict[str, Any]) -> Dict[str, Any] | None:
    path_value = proposal.get("linked_verdict_export_json")
    if not path_value:
        return None
    path = Path(str(path_value))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _trace_from_proposal(proposal: Dict[str, Any], trace_path: Path = SYSTEM_LOG_PATH) -> Dict[str, Any] | None:
    linked = proposal.get("linked_decision_trace_id")
    if not linked:
        return None
    trace = read_trace_by_proposal_id(str(linked), path=trace_path)
    return trace if isinstance(trace, dict) else None


def build_dossier_payload(
    proposal_id: str,
    *,
    history_path: Path = PROPOSAL_HISTORY_PATH,
    trace_path: Path = SYSTEM_LOG_PATH,
) -> Dict[str, Any]:
    proposal = get_proposal(proposal_id, path=history_path)
    if proposal is None:
        raise KeyError(f"Proposal not found: {proposal_id}")
    verdict = _load_linked_verdict(proposal)
    trace = _trace_from_proposal(proposal, trace_path)
    source = verdict or trace or {}
    return {
        "version": SYSTEM_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "proposal": {
            "proposal_id": proposal.get("proposal_id"),
            "created_at": proposal.get("created_at"),
            "updated_at": proposal.get("updated_at"),
            "source": proposal.get("source"),
            "template_id": proposal.get("template_id"),
            "title": proposal.get("title"),
            "body": proposal.get("body"),
            "taxonomy_hint": proposal.get("taxonomy_hint"),
            "status": proposal.get("status"),
            "decision_status": proposal.get("decision_status"),
            "parent_proposal_id": proposal.get("parent_proposal_id"),
        },
        "decision": {
            "linked_decision_trace_id": proposal.get("linked_decision_trace_id"),
            "decision_timestamp": proposal.get("decision_timestamp") or source.get("timestamp"),
            "taxonomy": source.get("taxonomy") or source.get("proposal_taxonomy"),
            "votes": source.get("votes") or source.get("monolith_votes") or {},
            "confidence": source.get("confidence"),
            "final_verdict": source.get("final_verdict") or source.get("verdict"),
            "terminal_branch": source.get("terminal_branch"),
            "review_triggers": source.get("review_triggers", []),
        },
        "references": {
            "history_path": str(history_path),
            "trace_path": str(trace_path),
            "linked_verdict_path": proposal.get("linked_verdict_path"),
            "linked_verdict_export_json": proposal.get("linked_verdict_export_json"),
            "linked_verdict_export_md": proposal.get("linked_verdict_export_md"),
        },
    }


def _markdown(payload: Dict[str, Any]) -> str:
    proposal = payload["proposal"]
    decision = payload["decision"]
    references = payload["references"]
    votes = decision.get("votes", {})
    if isinstance(votes, dict):
        vote_lines = [
            f"- `{agent}`: `{vote.get('vote', vote) if isinstance(vote, dict) else vote}`"
            for agent, vote in votes.items()
        ]
    else:
        vote_lines = [f"- `{votes}`"]
    return (
        f"# Tribunal Dossier: {proposal.get('title')}\n\n"
        "## Proposal\n\n"
        f"- Proposal ID: `{proposal.get('proposal_id')}`\n"
        f"- Template: `{proposal.get('template_id') or 'manual'}`\n"
        f"- Status: `{proposal.get('status')}`\n"
        f"- Decision status: `{proposal.get('decision_status')}`\n"
        f"- Created: `{proposal.get('created_at')}`\n\n"
        "### Submitted Content\n\n"
        f"```text\n{proposal.get('body') or ''}\n```\n\n"
        "## Verdict\n\n"
        f"- Final verdict: `{decision.get('final_verdict')}`\n"
        f"- Taxonomy: `{decision.get('taxonomy')}`\n"
        f"- Confidence: `{decision.get('confidence')}`\n"
        f"- Terminal branch: `{decision.get('terminal_branch')}`\n"
        f"- Review triggers: `{decision.get('review_triggers')}`\n"
        f"- Decision timestamp: `{decision.get('decision_timestamp')}`\n\n"
        "## Monolith Votes\n\n"
        + "\n".join(vote_lines)
        + "\n\n## References\n\n"
        f"- Trace: `{decision.get('linked_decision_trace_id')}`\n"
        f"- Verdict JSON: `{references.get('linked_verdict_export_json')}`\n"
        f"- Verdict Markdown: `{references.get('linked_verdict_export_md')}`\n"
    )


def export_dossier(
    proposal_id: str,
    *,
    output_dir: Path = DOSSIER_DIR,
    history_path: Path = PROPOSAL_HISTORY_PATH,
    trace_path: Path = SYSTEM_LOG_PATH,
) -> Dict[str, Any]:
    payload = build_dossier_payload(proposal_id, history_path=history_path, trace_path=trace_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_id = _safe_id(proposal_id)
    json_path = output_dir / f"{safe_id}_dossier.json"
    markdown_path = output_dir / f"{safe_id}_dossier.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    markdown_path.write_text(_markdown(payload), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path), "payload": payload}


def latest_dossier_export_status(output_dir: Path = DOSSIER_DIR) -> Dict[str, Any]:
    if not output_dir.exists():
        return {"path": str(output_dir), "latest_json": None, "latest_markdown": None}
    json_files = list(output_dir.glob("*_dossier.json"))
    md_files = list(output_dir.glob("*_dossier.md"))
    latest_json = max(json_files, key=lambda path: path.stat().st_mtime) if json_files else None
    latest_md = max(md_files, key=lambda path: path.stat().st_mtime) if md_files else None
    return {
        "path": str(output_dir),
        "latest_json": str(latest_json) if latest_json else None,
        "latest_markdown": str(latest_md) if latest_md else None,
    }


__all__ = ["DOSSIER_DIR", "build_dossier_payload", "export_dossier", "latest_dossier_export_status"]
