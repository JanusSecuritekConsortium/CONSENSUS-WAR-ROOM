from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from core.paths import ARBITER_DIR


DATA_SOURCE_CACHE_DIR = ARBITER_DIR / "cache" / "data_sources"


class DataSourceCache:
    def __init__(self, root: Path = DATA_SOURCE_CACHE_DIR) -> None:
        self.root = root

    def _path(self, source_id: str, query: str = "") -> Path:
        digest = hashlib.sha256(query.encode("utf-8", errors="replace")).hexdigest()[:16]
        return self.root / source_id / f"{digest}.json"

    def write(self, source_id: str, query: str, items: list[Dict[str, Any]], fetched_at: str | None = None) -> Path:
        path = self._path(source_id, query)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"source": source_id, "query_hash": path.stem, "fetched_at": fetched_at or _now(), "items": items}
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        temp.replace(path)
        return path

    def read(self, source_id: str, query: str = "", ttl_seconds: int = 900) -> Dict[str, Any] | None:
        path = self._path(source_id, query)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        fetched_at = _parse(payload.get("fetched_at"))
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds() if fetched_at else None
        payload["cache_path"] = str(path)
        payload["age_seconds"] = round(age, 3) if age is not None else None
        payload["freshness"] = "fresh" if age is not None and age <= ttl_seconds else "stale"
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
