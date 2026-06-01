from __future__ import annotations

from typing import Any, Dict, List

from core.data_sources.models import DataSourceAdapter, NormalizedDataItem
from core.data_sources.normalization import stable_item_id, text, utc_now_iso
from integrations.rss.probe import probe_feed


class RssAdapter(DataSourceAdapter):
    source_id = "rss"
    display_name = "Public RSS"
    source_type = "public_news_feed"

    def health_check(self) -> Dict[str, Any]:
        configured = bool(self.config.get("feeds"))
        return {"source_id": self.source_id, "status": "READY" if self.enabled and configured else ("DISABLED" if not self.enabled else "SOURCE_NOT_CONFIGURED"), "enabled": self.enabled}

    def fetch(self, query: str = "", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        health = self.health_check()
        if health["status"] != "READY":
            return {"source": self.source_id, "status": health["status"], "items": [], "fetched_at": utc_now_iso()}
        items: List[Dict[str, Any]] = []
        for feed in self.config.get("feeds", []):
            result = probe_feed(feed, session=self.session)
            if result.status != "READY":
                continue
            for item in result.entries[:20]:
                items.append({
                    "title": item.get("title", ""),
                    "summary": item.get("excerpt", ""),
                    "url": item.get("url", ""),
                    "published_at": item.get("published_at", ""),
                    "topics": feed.get("taxonomy_tags", feed.get("topics", [])),
                })
        return {"source": self.source_id, "status": "READY", "items": items, "fetched_at": utc_now_iso()}

    def normalize(self, raw_items: List[Dict[str, Any]]) -> List[NormalizedDataItem]:
        now = utc_now_iso()
        return [
            NormalizedDataItem(
                item_id=stable_item_id(self.source_id, item.get("url"), item.get("title")),
                source=self.source_id, source_type=self.source_type, title=text(item.get("title")),
                summary=text(item.get("summary")), url=text(item.get("url")),
                published_at=text(item.get("published_at")), fetched_at=now,
                topics=[str(topic) for topic in item.get("topics", [])], confidence=0.5, credibility=0.6,
                raw_ref=text(item.get("url")) or None,
            ) for item in raw_items if isinstance(item, dict)
        ]
