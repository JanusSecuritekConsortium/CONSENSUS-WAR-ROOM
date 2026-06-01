from __future__ import annotations

from typing import Any, Dict, List

from core.data_sources.models import DataSourceAdapter, NormalizedDataItem
from core.data_sources.normalization import stable_item_id, text, utc_now_iso


class SearchAdapter(DataSourceAdapter):
    source_id = "search"
    display_name = "Configured Search Provider"
    source_type = "search_result"
    requires_credentials = True

    def health_check(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"source_id": self.source_id, "status": "DISABLED", "enabled": False}
        configured = bool(self.config.get("provider") and self.config.get("base_url"))
        return {"source_id": self.source_id, "status": "READY" if configured else "SOURCE_NOT_CONFIGURED", "enabled": True}

    def fetch(self, query: str = "", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {"source": self.source_id, "status": self.health_check()["status"], "items": [], "fetched_at": utc_now_iso()}

    def normalize(self, raw_items: List[Dict[str, Any]]) -> List[NormalizedDataItem]:
        now = utc_now_iso()
        return [
            NormalizedDataItem(
                item_id=stable_item_id(self.source_id, item.get("url"), item.get("title")),
                source=self.source_id, source_type=self.source_type, title=text(item.get("title")),
                summary=text(item.get("summary")), url=text(item.get("url")),
                published_at=text(item.get("published_at")), fetched_at=now,
                topics=["search"], confidence=0.4, credibility=0.4, raw_ref=text(item.get("url")) or None,
            ) for item in raw_items if isinstance(item, dict)
        ]
