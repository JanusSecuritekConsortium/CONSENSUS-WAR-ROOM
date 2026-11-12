from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from core.logging import log_files
from core.paths import SYSTEM_LOG_PATH


def _log_lines_newest_first(path: Path) -> Iterator[str]:
    """Lines of the log and of its rotated earlier parts, newest first.

    Each part is only opened when the search reaches it, so a caller that stops
    at the first match never reads the older parts."""
    for part in reversed(log_files(path)):
        try:
            text = part.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        yield from reversed(text.splitlines())


def _iter_traces_newest_first(path: Path = SYSTEM_LOG_PATH) -> Iterator[Dict[str, Any]]:
    for line in _log_lines_newest_first(path):
        # Most log lines are other events; skip them without decoding them.
        if "decision_trace" not in line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or record.get("event_type") != "decision_trace":
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        yield {
            "timestamp": record.get("timestamp"),
            "level": record.get("level"),
            **payload,
        }


def _iter_trace_records(path: Path = SYSTEM_LOG_PATH) -> List[Dict[str, Any]]:
    """Every decision trace, oldest first."""
    records = list(_iter_traces_newest_first(path))
    records.reverse()
    return records


def read_latest_trace(path: Path = SYSTEM_LOG_PATH) -> Optional[Dict[str, Any]]:
    return next(_iter_traces_newest_first(path), None)


def read_trace_by_proposal_id(proposal_id: str, path: Path = SYSTEM_LOG_PATH) -> Optional[Dict[str, Any]]:
    for record in _iter_traces_newest_first(path):
        if record.get("proposal_id") == proposal_id:
            return record
    return None


def list_recent_traces(limit: int = 10, path: Path = SYSTEM_LOG_PATH) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []
    records: List[Dict[str, Any]] = []
    for record in _iter_traces_newest_first(path):
        records.append(record)
        if len(records) >= limit:
            break
    records.reverse()
    return records
