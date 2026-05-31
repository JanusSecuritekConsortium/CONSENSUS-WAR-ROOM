from __future__ import annotations

from typing import Any, Dict, List

import requests

from core.data_sources.models import DataSourceAdapter, NormalizedDataItem
from core.data_sources.normalization import listify, stable_item_id, text, utc_now_iso


class GdeltAdapter(DataSourceAdapter):
    source_id = "gdelt"
    display_name = "GDELT DOC 2.0"
    source_type = "open_event_search"

    def health_check(self) -> Dict[str, Any]:
        return {"source_id": self.source_id, "status": "READY" if self.enabled else "DISABLED", "enabled": self.enabled}

    def fetch(self, query: str = "", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self.enabled:
            return _result(self.source_id, "DISABLED")
        session = self.session or requests
        response = session.get(
            self.config.get("base_url"),
            params={"query": query or "geopolitics", "mode": "ArtList", "maxrecords": 25, "format": "json"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("articles", []) if isinstance(payload, dict) else []
        return _result(self.source_id, "READY", items)

    def normalize(self, raw_items: List[Dict[str, Any]]) -> List[NormalizedDataItem]:
        fetched_at = utc_now_iso()
        return [
            NormalizedDataItem(
                item_id=stable_item_id(self.source_id, item.get("url"), item.get("title")),
                source=self.source_id,
                source_type=self.source_type,
                title=text(item.get("title")),
                summary=text(item.get("seendate") or item.get("summary")),
                url=text(item.get("url")),
                published_at=text(item.get("seendate") or item.get("published_at")),
                fetched_at=fetched_at,
                geography=listify(item.get("sourcecountry")),
                actors=[],
                topics=listify(item.get("domain")),
                confidence=0.6,
                credibility=0.6,
                raw_ref=text(item.get("url")) or None,
            )
            for item in raw_items
            if isinstance(item, dict)
        ]


def _result(source: str, status: str, items: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    return {"source": source, "status": status, "items": items or [], "fetched_at": utc_now_iso()}
