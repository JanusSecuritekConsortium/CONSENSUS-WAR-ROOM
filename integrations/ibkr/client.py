from __future__ import annotations

from typing import Any, Dict, List

import requests

from core.data_sources.models import DataSourceAdapter, NormalizedDataItem
from core.data_sources.normalization import stable_item_id, text, utc_now_iso


class IbkrAdapter(DataSourceAdapter):
    source_id = "ibkr"
    display_name = "Interactive Brokers Client Portal"
    source_type = "market_data"
    requires_credentials = True
    READ_ONLY_PATHS = ("/iserver/marketdata/snapshot", "/portfolio/accounts", "/portfolio/subaccounts")

    def health_check(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"source_id": self.source_id, "status": "DISABLED", "enabled": False, "read_only": True}
        if not self.config.get("base_url"):
            return {"source_id": self.source_id, "status": "MISSING_CREDENTIALS", "enabled": True, "read_only": True, "missing_credentials": ["IBKR_BASE_URL"]}
        return {"source_id": self.source_id, "status": "READY", "enabled": True, "read_only": True}

    def fetch(self, query: str = "", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        health = self.health_check()
        if health["status"] != "READY":
            return {"source": self.source_id, "status": health["status"], "items": [], "fetched_at": utc_now_iso()}
        context = context or {}
        path = str(context.get("path") or "/iserver/marketdata/snapshot")
        if path not in self.READ_ONLY_PATHS:
            raise PermissionError(f"IBKR read-only guard rejected endpoint: {path}")
        response = (self.session or requests).get(f"{str(self.config['base_url']).rstrip('/')}{path}", params=context.get("params") or {}, timeout=10)
        response.raise_for_status()
        payload = response.json()
        return {"source": self.source_id, "status": "READY", "items": payload if isinstance(payload, list) else [payload], "fetched_at": utc_now_iso()}

    def place_order(self, *_: Any, **__: Any) -> None:
        raise PermissionError("IBKR adapter is read-only; order placement is disabled.")

    def normalize(self, raw_items: List[Dict[str, Any]]) -> List[NormalizedDataItem]:
        now = utc_now_iso()
        return [
            NormalizedDataItem(
                item_id=stable_item_id(self.source_id, item.get("conid"), item.get("symbol")),
                source=self.source_id, source_type=self.source_type,
                title=text(item.get("symbol") or item.get("conid"), "Market instrument"),
                summary="Read-only market snapshot", url="", published_at=now, fetched_at=now,
                topics=["market_data"], confidence=0.7, credibility=0.8,
                raw_ref=text(item.get("conid")) or None,
            ) for item in raw_items if isinstance(item, dict)
        ]
