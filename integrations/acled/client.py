from __future__ import annotations

from typing import Any, Dict, List

import requests

from core.data_sources.models import DataSourceAdapter, NormalizedDataItem
from core.data_sources.normalization import clamp_score, listify, stable_item_id, text, utc_now_iso


class AcledAdapter(DataSourceAdapter):
    source_id = "acled"
    display_name = "ACLED"
    source_type = "conflict_event"
    requires_credentials = True

    def _token(self) -> str:
        return str(self.config.get("access_token") or self.config.get("token") or "")

    def _headers(self) -> Dict[str, str]:
        token = self._token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        email = str(self.config.get("email") or "")
        password = str(self.config.get("password") or "")
        if not email or not password:
            return {}
        session = self.session or requests
        response = session.post(
            self.config.get("token_url", "https://acleddata.com/oauth/token"),
            data={"username": email, "password": password, "grant_type": "password", "client_id": "acled"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        return {"Authorization": f"Bearer {payload['access_token']}"} if payload.get("access_token") else {}

    def health_check(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"source_id": self.source_id, "status": "DISABLED", "enabled": False}
        if not self._token() and not (self.config.get("email") and self.config.get("password")):
            return {"source_id": self.source_id, "status": "MISSING_CREDENTIALS", "enabled": True, "missing_credentials": ["ACLED_ACCESS_TOKEN or ACLED_EMAIL + ACLED_PASSWORD"]}
        return {"source_id": self.source_id, "status": "READY", "enabled": True}

    def fetch(self, query: str = "", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        health = self.health_check()
        if health["status"] != "READY":
            return {"source": self.source_id, "status": health["status"], "items": [], "fetched_at": utc_now_iso()}
        session = self.session or requests
        response = session.get(
            self.config.get("base_url"),
            headers=self._headers(),
            params={"limit": 50},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        return {"source": self.source_id, "status": "READY", "items": payload.get("data", []), "fetched_at": utc_now_iso()}

    def normalize(self, raw_items: List[Dict[str, Any]]) -> List[NormalizedDataItem]:
        fetched_at = utc_now_iso()
        return [
            NormalizedDataItem(
                item_id=stable_item_id(self.source_id, item.get("event_id_cnty"), item.get("event_date")),
                source=self.source_id,
                source_type=self.source_type,
                title=text(item.get("event_type"), "Conflict event"),
                summary=text(item.get("notes")),
                url="",
                published_at=text(item.get("event_date")),
                fetched_at=fetched_at,
                geography=listify([item.get("country"), item.get("admin1")]),
                actors=listify([item.get("actor1"), item.get("actor2")]),
                topics=listify([item.get("event_type"), item.get("sub_event_type")]),
                confidence=clamp_score(item.get("geo_precision"), 0.6),
                credibility=0.8,
                raw_ref=text(item.get("event_id_cnty")) or None,
            )
            for item in raw_items
            if isinstance(item, dict)
        ]
