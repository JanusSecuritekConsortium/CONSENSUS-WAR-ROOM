from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable, List


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_item_id(source: str, *parts: Any) -> str:
    value = "|".join([source, *[str(part or "") for part in parts]])
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:24]


def listify(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, Iterable):
        return [str(part).strip() for part in value if str(part).strip()]
    return [str(value)]


def clamp_score(value: Any, default: float = 0.0) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return default


def text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()
