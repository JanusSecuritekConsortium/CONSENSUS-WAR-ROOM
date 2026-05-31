from __future__ import annotations

from typing import Any, Dict, List

from core.data_sources.models import DataSourceAdapter, NormalizedDataItem
from core.data_sources.normalization import utc_now_iso


class GroundNewsAdapter(DataSourceAdapter):
    source_id = "ground_news"
    display_name = "Ground News"
    source_type = "media_bias_context"
    requires_credentials = True

    def health_check(self) -> Dict[str, Any]:
        configured = bool(self.config.get("official_api_enabled") and self.config.get("api_key") and self.config.get("base_url"))
        return {
            "source_id": self.source_id,
            "status": "READY" if self.enabled and configured else ("DISABLED" if not self.enabled else "OFFICIAL_ACCESS_REQUIRED"),
            "enabled": self.enabled,
            "scraping_allowed": False,
        }

    def fetch(self, query: str = "", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {"source": self.source_id, "status": self.health_check()["status"], "items": [], "fetched_at": utc_now_iso()}

    def normalize(self, raw_items: List[Dict[str, Any]]) -> List[NormalizedDataItem]:
        return []
