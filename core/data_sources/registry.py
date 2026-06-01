from __future__ import annotations

from typing import Any, Dict, Iterable, List

from core.data_sources.cache import DataSourceCache
from core.data_sources.models import DataSourceAdapter, NormalizedDataItem
from core.data_sources.source_config import load_data_source_config
from core.data_sources.normalization import utc_now_iso
from integrations.acled.client import AcledAdapter
from integrations.factal.client import FactalAdapter
from integrations.gdelt.client import GdeltAdapter
from integrations.ground_news.client import GroundNewsAdapter
from integrations.ibkr.client import IbkrAdapter
from integrations.rss.client import RssAdapter
from integrations.search.client import SearchAdapter


ADAPTER_TYPES = {
    "acled": AcledAdapter,
    "gdelt": GdeltAdapter,
    "factal": FactalAdapter,
    "ground_news": GroundNewsAdapter,
    "ibkr": IbkrAdapter,
    "rss": RssAdapter,
    "search": SearchAdapter,
}
ROLE_SOURCES = {
    "bellator": ("acled", "gdelt", "factal", "rss", "search"),
    "aeternum": ("ibkr", "gdelt", "rss", "search"),
}


class DataSourceRegistry:
    def __init__(
        self,
        config: Dict[str, Any] | None = None,
        adapters: Dict[str, DataSourceAdapter] | None = None,
        cache: DataSourceCache | None = None,
    ) -> None:
        self.config = config or load_data_source_config()
        sources = self.config.get("sources", {})
        self.adapters = adapters or {source_id: adapter_type(sources.get(source_id, {})) for source_id, adapter_type in ADAPTER_TYPES.items()}
        self.cache = cache or DataSourceCache()

    def list_adapters(self) -> List[DataSourceAdapter]:
        return [self.adapters[key] for key in sorted(self.adapters)]

    def health(self) -> List[Dict[str, Any]]:
        return [adapter.health_check() for adapter in self.list_adapters()]

    def collect(self, role: str, query: str = "", *, live: bool = False) -> Dict[str, Any]:
        source_ids = ROLE_SOURCES.get(role.lower(), ())
        normalized: List[NormalizedDataItem] = []
        sources: Dict[str, Dict[str, Any]] = {}
        stale_sources: List[str] = []
        for source_id in source_ids:
            adapter = self.adapters[source_id]
            ttl = int(adapter.config.get("ttl_seconds", self.config.get("cache", {}).get("default_ttl_seconds", 900)))
            cached = self.cache.read(source_id, query, ttl)
            result: Dict[str, Any] | None = None
            if live and adapter.enabled:
                try:
                    result = adapter.fetch(query)
                except Exception as exc:
                    result = {"source": source_id, "status": "CLIENT_ERROR", "items": [], "error": str(exc), "fetched_at": utc_now_iso()}
                if result.get("status") == "READY":
                    items = [item.to_dict() for item in adapter.normalize(result.get("items", []))]
                    self.cache.write(source_id, query, items, str(result.get("fetched_at") or utc_now_iso()))
                    cached = self.cache.read(source_id, query, ttl)
            if cached:
                items = cached.get("items", [])
                normalized.extend(_items_from_dicts(items))
                if cached.get("freshness") == "stale":
                    stale_sources.append(source_id)
                sources[source_id] = {
                    "status": "CACHE_READY" if cached.get("freshness") == "fresh" else "CACHE_STALE",
                    "freshness": cached.get("freshness"),
                    "fetched_at": cached.get("fetched_at"),
                    "item_count": len(items),
                }
            else:
                health = adapter.health_check()
                sources[source_id] = {
                    "status": result.get("status") if result else health.get("status", "UNAVAILABLE"),
                    "freshness": "unavailable",
                    "fetched_at": result.get("fetched_at") if result else None,
                    "item_count": 0,
                }
        return {
            "role": role.lower(),
            "status": "DATA_AVAILABLE" if normalized else "DATA_UNAVAILABLE",
            "mode": "live" if live else "cache_only",
            "items": [item.to_dict() for item in normalized],
            "sources": sources,
            "stale_sources": stale_sources,
            "generated_at": utc_now_iso(),
            "operator_note": "Use only normalized source items. If DATA_UNAVAILABLE, do not infer or invent external intelligence.",
        }


def _items_from_dicts(items: Iterable[Dict[str, Any]]) -> List[NormalizedDataItem]:
    result: List[NormalizedDataItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        fields = {field: item.get(field) for field in NormalizedDataItem.__dataclass_fields__}
        fields["geography"] = list(fields.get("geography") or [])
        fields["actors"] = list(fields.get("actors") or [])
        fields["topics"] = list(fields.get("topics") or [])
        result.append(NormalizedDataItem(**fields))
    return result


def build_data_source_registry(config: Dict[str, Any] | None = None) -> DataSourceRegistry:
    return DataSourceRegistry(config=config)
