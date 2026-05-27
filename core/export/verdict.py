from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from config.version import SYSTEM_VERSION
from core.decision_trace import read_latest_trace
from core.paths import SYSTEM_LOG_PATH, SYSTEM_ROOT


VERDICT_DIR = SYSTEM_ROOT / "reports" / "verdicts"


def _safe_proposal_id(value: Any) -> str:
    text = str(value or "unknown").strip() or "unknown"
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in text)[:96]


def _votes_from_trace(trace: Dict[str, Any]) -> Any:
    votes = trace.get("votes")
    if votes is None:
        votes = trace.get("monolith_votes")
    return votes if votes is not None else {}


def _verdict_payload(trace: Dict[str, Any], source_trace_path: Path = SYSTEM_LOG_PATH) -> Dict[str, Any]:
    proposal_id = trace.get("proposal_id") or trace.get("session_id") or "unknown"
    return {
        "version": SYSTEM_VERSION,
        "proposal_id": proposal_id,
        "timestamp": trace.get("timestamp") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "taxonomy": trace.get("taxonomy") or trace.get("proposal_taxonomy") or trace.get("proposal_classification", {}).get("taxonomy"),
        "votes": _votes_from_trace(trace),
        "confidence": trace.get("confidence"),
        "final_verdict": trace.get("final_verdict") or trace.get("verdict"),
        "terminal_branch": trace.get("terminal_branch"),
        "review_triggers": trace.get("review_triggers", []),
        "source_trace_path": str(source_trace_path),
    }


def _markdown(payload: Dict[str, Any]) -> str:
    votes = payload.get("votes", {})
    if isinstance(votes, dict):
        vote_lines = [f"- `{key}`: `{value.get('vote', value) if isinstance(value, dict) else value}`" for key, value in votes.items()]
    else:
        vote_lines = [f"- `{votes}`"]
    return (
        f"# Latest Verdict: {payload.get('proposal_id')}\n\n"
        f"- Version: `{payload.get('version')}`\n"
        f"- Timestamp: `{payload.get('timestamp')}`\n"
        f"- Taxonomy: `{payload.get('taxonomy')}`\n"
        f"- Confidence: `{payload.get('confidence')}`\n"
        f"- Final verdict: `{payload.get('final_verdict')}`\n"
        f"- Terminal branch: `{payload.get('terminal_branch')}`\n"
        f"- Review triggers: `{payload.get('review_triggers')}`\n"
        f"- Source trace: `{payload.get('source_trace_path')}`\n\n"
        "## Votes\n\n"
        + "\n".join(vote_lines)
        + "\n"
    )


def export_latest_verdict(
    trace: Dict[str, Any] | None = None,
    *,
    output_dir: Path = VERDICT_DIR,
    source_trace_path: Path = SYSTEM_LOG_PATH,
) -> Dict[str, Any]:
    latest_trace = trace or read_latest_trace(source_trace_path)
    if not isinstance(latest_trace, dict) or not latest_trace:
        raise RuntimeError("No decision trace available for verdict export.")
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = _verdict_payload(latest_trace, source_trace_path)
    proposal_id = _safe_proposal_id(payload.get("proposal_id"))
    json_path = output_dir / f"latest_verdict_{proposal_id}.json"
    markdown_path = output_dir / f"latest_verdict_{proposal_id}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    markdown_path.write_text(_markdown(payload), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(markdown_path), "payload": payload}


def latest_verdict_export_status(output_dir: Path = VERDICT_DIR) -> Dict[str, Any]:
    if not output_dir.exists():
        return {"path": str(output_dir), "latest_json": None, "latest_markdown": None}
    json_files = list(output_dir.glob("latest_verdict_*.json"))
    md_files = list(output_dir.glob("latest_verdict_*.md"))
    latest_json = max(json_files, key=lambda path: path.stat().st_mtime) if json_files else None
    latest_md = max(md_files, key=lambda path: path.stat().st_mtime) if md_files else None
    return {
        "path": str(output_dir),
        "latest_json": str(latest_json) if latest_json else None,
        "latest_markdown": str(latest_md) if latest_md else None,
    }


__all__ = ["VERDICT_DIR", "export_latest_verdict", "latest_verdict_export_status"]
