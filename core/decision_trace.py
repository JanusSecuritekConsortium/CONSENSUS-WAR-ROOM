from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from core.logging import log_files
from core.paths import SYSTEM_LOG_PATH


def _log_lines(path: Path) -> Iterator[str]:
    """Lines of the log and of its rotated earlier parts, oldest first."""
    for part in log_files(path):
        try:
            text = part.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        yield from text.splitlines()


def _iter_trace_records(path: Path = SYSTEM_LOG_PATH) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line in _log_lines(path):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or record.get("event_type") != "decision_trace":
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        records.append(
            {
                "timestamp": record.get("timestamp"),
                "level": record.get("level"),
                **payload,
            }
        )
    return records


def read_latest_trace(path: Path = SYSTEM_LOG_PATH) -> Optional[Dict[str, Any]]:
    records = _iter_trace_records(path)
    return records[-1] if records else None


def read_trace_by_proposal_id(proposal_id: str, path: Path = SYSTEM_LOG_PATH) -> Optional[Dict[str, Any]]:
    for record in reversed(_iter_trace_records(path)):
        if record.get("proposal_id") == proposal_id:
            return record
    return None


def list_recent_traces(limit: int = 10, path: Path = SYSTEM_LOG_PATH) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []
    return _iter_trace_records(path)[-limit:]
