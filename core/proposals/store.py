from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.paths import SYSTEM_ROOT


PROPOSAL_HISTORY_PATH = SYSTEM_ROOT / "reports" / "proposal_history.jsonl"
VALID_STATUSES = {"DRAFT", "SUBMITTED", "RESUBMITTED", "ARCHIVED"}
VALID_DECISION_STATUSES = {"DRAFT", "SUBMITTED", "DECIDED", "NO_CONSENSUS", "ESCALATED", "ERROR", "ARCHIVED"}
VALID_SOURCES = {"manual", "template", "history_resend"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_proposal_id() -> str:
    return f"prop_{uuid.uuid4().hex[:12]}"


def _read_record_lines(path: Path = PROPOSAL_HISTORY_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("proposal_id"):
            records.append(record)
    return records


def _read_records(path: Path = PROPOSAL_HISTORY_PATH) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for record in _read_record_lines(path):
        proposal_id = str(record.get("proposal_id") or "")
        if not proposal_id:
            continue
        previous = by_id.get(proposal_id, {})
        merged = {**previous, **record}
        by_id[proposal_id] = merged
    return list(by_id.values())


def _append_record(record: Dict[str, Any], path: Path = PROPOSAL_HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")


def _normalize_status(status: str) -> str:
    normalized = status.upper()
    if normalized not in VALID_STATUSES:
        raise ValueError(f"Invalid proposal status: {status}")
    return normalized


def _normalize_decision_status(status: str) -> str:
    normalized = status.upper()
    if normalized not in VALID_DECISION_STATUSES:
        raise ValueError(f"Invalid proposal decision status: {status}")
    return normalized


def _normalize_source(source: str) -> str:
    normalized = source.lower()
    if normalized not in VALID_SOURCES:
        raise ValueError(f"Invalid proposal source: {source}")
    return normalized


def _derive_title(title: str | None, body: str) -> str:
    if title and title.strip():
        return title.strip()
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:96]
    return "Untitled Proposal"


def create_proposal(
    *,
    title: str | None,
    body: str,
    taxonomy_hint: str = "",
    source: str = "manual",
    template_id: str | None = None,
    status: str = "DRAFT",
    linked_decision_trace_id: str | None = None,
    parent_proposal_id: str | None = None,
    path: Path = PROPOSAL_HISTORY_PATH,
) -> Dict[str, Any]:
    clean_body = body.strip()
    if not clean_body:
        raise ValueError("Proposal body is empty.")
    now = _utc_now()
    record: Dict[str, Any] = {
        "proposal_id": _new_proposal_id(),
        "created_at": now,
        "updated_at": now,
        "source": _normalize_source(source),
        "template_id": template_id,
        "title": _derive_title(title, clean_body),
        "body": clean_body,
        "taxonomy_hint": taxonomy_hint.strip(),
        "status": _normalize_status(status),
        "decision_status": "SUBMITTED" if _normalize_status(status) in {"SUBMITTED", "RESUBMITTED"} else _normalize_status(status),
        "linked_decision_trace_id": linked_decision_trace_id,
        "linked_verdict_path": None,
        "linked_verdict_export_json": None,
        "linked_verdict_export_md": None,
        "decision_timestamp": None,
        "parent_proposal_id": parent_proposal_id,
    }
    _append_record(record, path)
    return dict(record)


def list_recent_proposals(
    limit: int = 20,
    *,
    include_archived: bool = False,
    path: Path = PROPOSAL_HISTORY_PATH,
) -> List[Dict[str, Any]]:
    records = _read_records(path)
    if not include_archived:
        records = [record for record in records if record.get("status") != "ARCHIVED"]
    records.sort(key=lambda record: str(record.get("created_at", "")), reverse=True)
    return [dict(record) for record in records[:limit]]


def get_proposal(proposal_id: str, *, path: Path = PROPOSAL_HISTORY_PATH) -> Dict[str, Any] | None:
    for record in _read_records(path):
        if record.get("proposal_id") == proposal_id:
            return dict(record)
    return None


def update_proposal(
    proposal_id: str,
    *,
    path: Path = PROPOSAL_HISTORY_PATH,
    **updates: Any,
) -> Dict[str, Any]:
    allowed = {
        "title",
        "body",
        "taxonomy_hint",
        "status",
        "decision_status",
        "linked_decision_trace_id",
        "linked_verdict_path",
        "linked_verdict_export_json",
        "linked_verdict_export_md",
        "decision_timestamp",
        "template_id",
    }
    updated_record: Dict[str, Any] | None = None
    current = get_proposal(proposal_id, path=path)
    if current is not None:
        record = dict(current)
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "status":
                record[key] = _normalize_status(str(value))
                if record[key] == "ARCHIVED":
                    record["decision_status"] = "ARCHIVED"
            elif key == "decision_status":
                record[key] = _normalize_decision_status(str(value))
            else:
                record[key] = value
        record["updated_at"] = _utc_now()
        record["revision_event"] = "proposal_update"
        updated_record = dict(record)
    if updated_record is None:
        raise KeyError(f"Proposal not found: {proposal_id}")
    _append_record(updated_record, path)
    return updated_record


def archive_proposal(proposal_id: str, *, path: Path = PROPOSAL_HISTORY_PATH) -> Dict[str, Any]:
    return update_proposal(proposal_id, path=path, status="ARCHIVED")


def resend_proposal(proposal_id: str, *, path: Path = PROPOSAL_HISTORY_PATH) -> Dict[str, Any]:
    original = get_proposal(proposal_id, path=path)
    if original is None:
        raise KeyError(f"Proposal not found: {proposal_id}")
    return create_proposal(
        title=original.get("title"),
        body=str(original.get("body", "")),
        taxonomy_hint=str(original.get("taxonomy_hint", "")),
        source="history_resend",
        template_id=original.get("template_id"),
        status="RESUBMITTED",
        parent_proposal_id=proposal_id,
        path=path,
    )


def duplicate_proposal(proposal_id: str, *, path: Path = PROPOSAL_HISTORY_PATH) -> Dict[str, Any]:
    original = get_proposal(proposal_id, path=path)
    if original is None:
        raise KeyError(f"Proposal not found: {proposal_id}")
    return create_proposal(
        title=f"Copy of {original.get('title', 'Untitled Proposal')}",
        body=str(original.get("body", "")),
        taxonomy_hint=str(original.get("taxonomy_hint", "")),
        source="history_resend",
        template_id=original.get("template_id"),
        status="DRAFT",
        parent_proposal_id=proposal_id,
        path=path,
    )


def proposal_history_status(path: Path = PROPOSAL_HISTORY_PATH) -> Dict[str, Any]:
    recent = list_recent_proposals(limit=20, path=path)
    counts = lifecycle_counts(path)
    return {
        "history_path": str(path),
        "recent_count": len(recent),
        "last_proposal_id": recent[0]["proposal_id"] if recent else None,
        "lifecycle_counts": counts,
    }


def lifecycle_counts(path: Path = PROPOSAL_HISTORY_PATH) -> Dict[str, int]:
    counts = {status: 0 for status in sorted(VALID_DECISION_STATUSES)}
    for record in _read_records(path):
        status = str(record.get("decision_status") or record.get("status") or "DRAFT").upper()
        if status not in counts:
            status = "ERROR"
        counts[status] += 1
    return counts


__all__ = [
    "PROPOSAL_HISTORY_PATH",
    "VALID_DECISION_STATUSES",
    "archive_proposal",
    "create_proposal",
    "duplicate_proposal",
    "get_proposal",
    "lifecycle_counts",
    "list_recent_proposals",
    "proposal_history_status",
    "resend_proposal",
    "update_proposal",
]
