"""Structured event log. Records ids, counts and error types, never message text."""
from __future__ import annotations

from datetime import datetime, timezone
import json

from . import config

MAX_BYTES = 1_000_000


def event(name: str, **fields) -> None:
    path = config.home() / 'system' / 'logs' / 'events.jsonl'
    record = {'at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'event': name, **fields}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > MAX_BYTES:
            path.replace(path.with_suffix('.1.jsonl'))
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + '\n')
    except OSError:
        pass  # Logging must never break a scan.


def recent(limit: int = 20) -> list[dict]:
    path = config.home() / 'system' / 'logs' / 'events.jsonl'
    try:
        lines = path.read_text(encoding='utf-8').splitlines()[-limit:]
    except OSError:
        return []
    return [json.loads(line) for line in lines if line.strip()]
