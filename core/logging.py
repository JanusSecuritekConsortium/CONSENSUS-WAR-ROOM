from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from core.paths import SYSTEM_LOG_PATH


def log_event(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    level: str = "INFO",
) -> None:
    SYSTEM_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "event_type": event_type,
        "payload": payload or {},
    }
    with SYSTEM_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, default=str) + "\n")


def log_error(event_type: str, error: Exception, payload: Optional[Dict[str, Any]] = None) -> None:
    error_payload = dict(payload or {})
    error_payload["error_type"] = error.__class__.__name__
    error_payload["error"] = str(error)
    log_event(event_type, error_payload, level="ERROR")


def fsync_file(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())

