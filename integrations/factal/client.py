from __future__ import annotations

from typing import Any, Dict, List

import requests

from core.data_sources.models import DataSourceAdapter, NormalizedDataItem
from core.data_sources.normalization import listify, stable_item_id, text, utc_now_iso


class FactalAdapter(DataSourceAdapter):
    source_id = "factal"
    display_name = "Factal"
    source_type = "verified_breaking_news"
    requires_credentials = True

    def health_check(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"source_id": self.source_id, "status": "DISABLED", "enabled": False}
        if not self.config.get("api_key") or not self.config.get("base_url"):
            return {"source_id": self.source_id, "status": "MISSING_CREDENTIALS", "enabled": True, "missing_credentials": ["FACTAL_API_KEY"]}
        return {"source_id": self.source_id, "status": "READY", "enabled": True}

    def fetch(self, query: str = "", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        health = self.health_check()
        if health["status"] != "READY":
            return {"source": self.source_id, "status": health["status"], "items": [], "fetched_at": utc_now_iso()}
        response = (self.session or requests).get(
            self.config["base_url"], headers={"Authorization": f"Bearer {self.config['api_key']}"}, params={"query": query}, timeout=10
        )
        response.raise_for_status()
        payload = response.json()
        return {"source": self.source_id, "status": "READY", "items": payload.get("items", []), "fetched_at": utc_now_iso()}

    def normalize(self, raw_items: List[Dict[str, Any]]) -> List[NormalizedDataItem]:
        now = utc_now_iso()
        return [
            NormalizedDataItem(
                item_id=stable_item_id(self.source_id, item.get("id"), item.get("title")),
                source=self.source_id, source_type=self.source_type, title=text(item.get("title")),
                summary=text(item.get("summary")), url=text(item.get("url")),
                published_at=text(item.get("published_at")), fetched_at=now,
                geography=listify(item.get("geography")), actors=listify(item.get("actors")),
                topics=listify(item.get("topics")), confidence=0.8, credibility=0.85,
                raw_ref=text(item.get("id")) or None,
            ) for item in raw_items if isinstance(item, dict)
        ]
