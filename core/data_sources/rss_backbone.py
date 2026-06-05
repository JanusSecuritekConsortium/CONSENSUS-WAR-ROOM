"""RSS-first Bellator intelligence ingestion and bounded retrieval."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from core.data_sources.rss_store import RssIntelligenceStore, parse_timestamp
from core.data_sources.source_config import load_data_source_config
from integrations.rss.probe import FeedProbeResult, probe_feed


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RssIntelligenceBackbone:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        *,
        store: RssIntelligenceStore | None = None,
        session: Any | None = None,
        now_fn: Callable[[], datetime] = _utc_now,
        probe_fn: Callable[..., FeedProbeResult] = probe_feed,
    ) -> None:
        self.config = config or load_data_source_config().get("sources", {}).get("rss", {})
        self.store = store or RssIntelligenceStore()
        self.session = session
        self.now_fn = now_fn
        self.probe_fn = probe_fn
        self.feeds = list(self.config.get("feeds", []))
        self.poll_interval_seconds = int(self.config.get("poll_interval_seconds", 1200))
        self.backoff_base_seconds = int(self.config.get("backoff_base_seconds", 300))
        self.backoff_max_seconds = int(self.config.get("backoff_max_seconds", 7200))
        self.store.sync_sources(self.feeds)

    def poll(self, *, force: bool = False) -> dict[str, Any]:
        now = self.now_fn()
        summary: dict[str, Any] = {
            "status": "READY",
            "attempted": 0,
            "skipped": 0,
            "failed": 0,
            "stored": 0,
            "deduplicated": 0,
            "sources": [],
            "polled_at": now.isoformat(),
        }
        for feed in self.feeds:
            source_id = str(feed.get("source_id") or feed.get("name"))
            source = self.store.source(source_id) or {}
            if not feed.get("enabled", True) or feed.get("quarantined", False):
                self.store.update_source(source_id, status="DISABLED", last_error=str(feed.get("quarantine_reason", "disabled")))
                summary["skipped"] += 1
                continue
            if not force and not self._is_due(source, now):
                summary["skipped"] += 1
                continue

            conditional: dict[str, str] = {}
            if source.get("etag"):
                conditional["If-None-Match"] = str(source["etag"])
            if source.get("last_modified"):
                conditional["If-Modified-Since"] = str(source["last_modified"])
            result = self.probe_fn(feed, session=self.session, conditional_headers=conditional)
            summary["attempted"] += 1
            if result.status == "READY":
                insert_summary = {"inserted": 0, "deduplicated": 0}
                if not result.not_modified:
                    insert_summary = self.store.upsert_items(
                        source_id,
                        result.entries,
                        taxonomy_tags=list(feed.get("taxonomy_tags", [])),
                        fetched_at=now.isoformat(),
                    )
                self.store.update_source(
                    source_id,
                    status="READY",
                    final_url=result.final_url,
                    etag=result.etag or source.get("etag", ""),
                    last_modified=result.last_modified or source.get("last_modified", ""),
                    http_status=result.http_status,
                    content_type=result.content_type,
                    last_error="",
                    failure_count=0,
                    last_attempt_at=now.isoformat(),
                    last_success_at=now.isoformat(),
                    next_poll_at=(now + timedelta(seconds=self.poll_interval_seconds)).isoformat(),
                )
                summary["stored"] += insert_summary["inserted"]
                summary["deduplicated"] += insert_summary["deduplicated"]
            else:
                failures = int(source.get("failure_count", 0)) + 1
                delay = min(self.backoff_base_seconds * (2 ** (failures - 1)), self.backoff_max_seconds)
                self.store.update_source(
                    source_id,
                    status=result.status,
                    final_url=result.final_url,
                    http_status=result.http_status,
                    content_type=result.content_type,
                    last_error=result.error,
                    failure_count=failures,
                    last_attempt_at=now.isoformat(),
                    next_poll_at=(now + timedelta(seconds=delay)).isoformat(),
                )
                summary["failed"] += 1
            source_result = result.to_dict()
            source_result["entry_count"] = len(source_result["entries"])
            source_result.pop("entries", None)
            summary["sources"].append(source_result)
        if summary["failed"]:
            summary["status"] = "DEGRADED"
        return summary

    def build_packet(
        self,
        query: str,
        *,
        taxonomy_tags: list[str] | None = None,
        limit: int = 12,
        live: bool = False,
    ) -> dict[str, Any]:
        poll_summary = self.poll() if live else None
        items = self.store.search(query, taxonomy_tags=taxonomy_tags, limit=min(limit, 12))
        fallback = bool(live and poll_summary and poll_summary["failed"] and items)
        mode = "CACHE_FALLBACK" if fallback else ("LIVE" if live else "CACHE_ONLY")
        return {
            "mode": mode,
            "status": "DATA_AVAILABLE" if items else "DATA_UNAVAILABLE",
            "query": query,
            "taxonomy_filter": taxonomy_tags or [],
            "item_count": len(items),
            "max_items": 12,
            "items": items,
            "citations": [{"title": item["title"], "source": item["source"], "url": item["url"]} for item in items],
            "poll_summary": poll_summary,
            "constraints": [
                "Use cited RSS items as bounded context only.",
                "Do not infer sentiment unless sentiment_confidence is explicitly present.",
                "Mark claims unsupported when no cited item supports them.",
            ],
        }

    def status(self) -> dict[str, Any]:
        status = self.store.status()
        now = self.now_fn()
        for source in status["source_health"]:
            next_poll = parse_timestamp(str(source.get("next_poll_at", "")))
            if source.get("status") == "READY" and next_poll is not None and next_poll < now:
                source["status"] = "STALE"
        status.update(
            {
                "mode": "RSS_PRIMARY",
                "poll_interval_seconds": self.poll_interval_seconds,
                "backoff_base_seconds": self.backoff_base_seconds,
                "backoff_max_seconds": self.backoff_max_seconds,
                "packet_item_limit": 12,
            }
        )
        return status

    @staticmethod
    def _is_due(source: dict[str, Any], now: datetime) -> bool:
        next_poll = parse_timestamp(str(source.get("next_poll_at", "")))
        return next_poll is None or next_poll <= now


def build_bellator_rss_packet(
    query: str,
    *,
    taxonomy_tags: list[str] | None = None,
    limit: int = 12,
    live: bool = False,
) -> dict[str, Any]:
    return RssIntelligenceBackbone().build_packet(query, taxonomy_tags=taxonomy_tags, limit=limit, live=live)


def rss_backbone_status() -> dict[str, Any]:
    return RssIntelligenceBackbone().status()
