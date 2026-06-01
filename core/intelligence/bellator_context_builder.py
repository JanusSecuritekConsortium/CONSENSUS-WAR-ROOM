from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

try:
    from core.paths import ARBITER_DIR
    from config.version import SYSTEM_VERSION
except ImportError:
    from ..paths import ARBITER_DIR
    from ...config.version import SYSTEM_VERSION

try:
    from .bellator_feed_normalizer import normalize_feed_result
    from .bellator_risk_scorer import score_events
    from .geospatial_filters import build_geo_filter_config, filter_and_weight_events
except ImportError:
    from core.intelligence.bellator_feed_normalizer import normalize_feed_result
    from core.intelligence.bellator_risk_scorer import score_events
    from core.intelligence.geospatial_filters import build_geo_filter_config, filter_and_weight_events

from core.data_sources.enrichment import build_bellator_data_enrichment
from core.data_sources.rss_backbone import build_bellator_rss_packet

try:
    from integrations.feeds.abuse_ch_client import fetch_urlhaus_recent
    from integrations.feeds.acled_client import fetch_acled_events
    from integrations.feeds.cloudflare_radar_client import fetch_cloudflare_outages
    from integrations.feeds.nasa_firms_client import fetch_nasa_firms_events
except ImportError:
    from CONSENSUS_SYSTEM.integrations.feeds.abuse_ch_client import fetch_urlhaus_recent
    from CONSENSUS_SYSTEM.integrations.feeds.acled_client import fetch_acled_events
    from CONSENSUS_SYSTEM.integrations.feeds.cloudflare_radar_client import fetch_cloudflare_outages
    from CONSENSUS_SYSTEM.integrations.feeds.nasa_firms_client import fetch_nasa_firms_events


FEED_CACHE_DIR = ARBITER_DIR / "cache" / "feeds"
PACKET_CACHE_PATH = FEED_CACHE_DIR / "bellator_context_packet.json"
ANTI_FABRICATION_INSTRUCTION = (
    "Do not infer or invent feed data. If a feed diagnostic says missing credentials, "
    "unavailable, disabled, empty, or stale, explicitly treat that source as unavailable."
)

FeedFetcher = Callable[[], Dict[str, Any]]


def build_bellator_context_packet(
    query: str = "",
    *,
    live: bool | None = None,
    now: datetime | None = None,
    limit: int = 14,
    aoi: str | None = None,
    countries: str | List[str] | None = None,
    max_events: int | str | None = None,
    min_severity: float | str | None = None,
) -> Dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    should_fetch_live = _live_enabled() if live is None else live
    FEED_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    raw_results = _collect_feed_results(should_fetch_live)
    normalized_events: List[Dict[str, Any]] = []
    sources: Dict[str, Dict[str, Any]] = {}

    for result in raw_results:
        source = str(result.get("source", "unknown"))
        events = normalize_feed_result(result)
        normalized_events.extend(events)
        sources[source] = {
            "ok": bool(result.get("ok")),
            "status": result.get("status", "unknown"),
            "raw_count": len(result.get("items", [])) if isinstance(result.get("items"), list) else 0,
            "normalized_count": len(events),
            "diagnostics": result.get("diagnostics", {}),
            "fetched_at": result.get("fetched_at"),
            "cache_path": str(_cache_path(source)),
        }

    recent_72h_raw = _filter_window(normalized_events, current, timedelta(hours=72))
    geo_config = build_geo_filter_config(
        aoi=aoi,
        countries=countries,
        max_events=max_events,
        min_severity=min_severity,
    )
    recent_72h, filter_diagnostics = filter_and_weight_events(recent_72h_raw, geo_config)
    recent_24h = _filter_window(recent_72h, current, timedelta(hours=24))
    compact_events = _compact_events(recent_72h, min(limit, geo_config.max_events))
    _apply_filtered_counts(sources, recent_72h)
    packet = {
        "label": "BELLATOR CONTEXT PACKET",
        "version": SYSTEM_VERSION,
        "generated_at": current.isoformat(),
        "query_hint": query[:220],
        "mode": "live" if should_fetch_live else "cache_only",
        "window": {
            "last_24h": {"hours": 24, "event_count": len(recent_24h)},
            "last_72h": {"hours": 72, "event_count": len(recent_72h)},
        },
        "feed_counts": {
            "raw_event_count": len(normalized_events),
            "recent_72h_raw_event_count": len(recent_72h_raw),
            "filtered_event_count": len(recent_72h),
            "strategically_relevant_event_count": filter_diagnostics["strategically_relevant_event_count"],
        },
        "filters": filter_diagnostics,
        "risk": score_events(recent_72h, now=current),
        "events": compact_events,
        "sources": sources,
        "rss_intelligence": build_bellator_rss_packet(query, live=False),
        "real_data_layer": build_bellator_data_enrichment(query, live=False),
        "cache_dir": str(FEED_CACHE_DIR),
        "anti_fabrication_instruction": ANTI_FABRICATION_INSTRUCTION,
        "operator_note": _operator_note(sources, compact_events),
    }
    _write_json(PACKET_CACHE_PATH, packet)
    return packet


def build_bellator_diagnostics_payload(packet: Dict[str, Any] | None = None) -> Dict[str, Any]:
    active_packet = packet if isinstance(packet, dict) else _read_json(PACKET_CACHE_PATH)
    if not isinstance(active_packet, dict):
        return {
            "available": False,
            "timestamp": "--",
            "enabled_sources": [],
            "unavailable_sources": [],
            "cache_age_seconds": None,
            "normalized_event_count": 0,
            "highest_severity": 0.0,
            "source_diagnostics_summary": "No Bellator Context Packet cache found.",
            "cache_path": str(PACKET_CACHE_PATH),
        }

    sources = active_packet.get("sources", {})
    if not isinstance(sources, dict):
        sources = {}
    enabled_sources = []
    unavailable_sources = []
    diagnostics_parts = []
    normalized_event_count = 0
    for source, payload in sorted(sources.items()):
        source_payload = payload if isinstance(payload, dict) else {}
        status = str(source_payload.get("status", "unknown"))
        if source_payload.get("ok") or status == "ok":
            enabled_sources.append(str(source))
        else:
            unavailable_sources.append(f"{source}:{status}")
        try:
            normalized_event_count += int(source_payload.get("normalized_count", 0) or 0)
        except (TypeError, ValueError):
            pass
        diagnostics_parts.append(f"{source}:{status}")

    risk = active_packet.get("risk", {})
    if not isinstance(risk, dict):
        risk = {}
    return {
        "available": True,
        "timestamp": str(active_packet.get("generated_at") or "--"),
        "enabled_sources": enabled_sources,
        "unavailable_sources": unavailable_sources,
        "cache_age_seconds": _cache_age_seconds(active_packet.get("generated_at")),
        "normalized_event_count": normalized_event_count,
        "highest_severity": float(risk.get("max_severity", 0.0) or 0.0),
        "source_diagnostics_summary": ", ".join(diagnostics_parts) or "No source diagnostics.",
        "cache_path": str(PACKET_CACHE_PATH),
    }


def _collect_feed_results(live: bool) -> List[Dict[str, Any]]:
    fetchers: Dict[str, FeedFetcher] = {
        "acled": lambda: fetch_acled_events(days=3),
        "nasa_firms": lambda: fetch_nasa_firms_events(days=3),
        "cloudflare_radar": lambda: fetch_cloudflare_outages(days=3),
        "abuse_ch_urlhaus": fetch_urlhaus_recent,
    }
    results: List[Dict[str, Any]] = []
    for source, fetcher in fetchers.items():
        if live:
            result = _safe_fetch(source, fetcher)
            _write_json(_cache_path(source), result)
            results.append(result)
            continue

        cached = _read_json(_cache_path(source))
        if isinstance(cached, dict):
            cached.setdefault("diagnostics", {})
            cached["diagnostics"]["cache_used"] = True
            results.append(cached)
        else:
            result = _disabled_result(source)
            _write_json(_cache_path(source), result)
            results.append(result)
    return results


def _safe_fetch(source: str, fetcher: FeedFetcher) -> Dict[str, Any]:
    try:
        result = fetcher()
    except Exception as exc:
        result = {
            "source": source,
            "ok": False,
            "status": "client_error",
            "items": [],
            "diagnostics": {"error": str(exc)},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    if not isinstance(result, dict):
        return {
            "source": source,
            "ok": False,
            "status": "client_error",
            "items": [],
            "diagnostics": {"error": f"unexpected result type: {type(result).__name__}"},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    result.setdefault("source", source)
    result.setdefault("items", [])
    result.setdefault("diagnostics", {})
    result.setdefault("fetched_at", datetime.now(timezone.utc).isoformat())
    return result


def _compact_events(events: Iterable[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    ranked = sorted(
        events,
        key=lambda event: (_float(event.get("severity")), str(event.get("timestamp", ""))),
        reverse=True,
    )
    compact = []
    for event in ranked[:limit]:
        compact.append(
            {
                "source": event.get("source"),
                "event_type": event.get("event_type"),
                "country": event.get("country"),
                "region": event.get("region"),
                "timestamp": event.get("timestamp"),
                "severity": event.get("severity"),
                "confidence": event.get("confidence"),
                "strategic_relevance_score": event.get("strategic_relevance_score"),
                "strategic_relevance_tags": event.get("strategic_relevance_tags", []),
                "summary": event.get("summary"),
                "tags": event.get("tags", [])[:6] if isinstance(event.get("tags"), list) else [],
            }
        )
    return compact


def _apply_filtered_counts(sources: Dict[str, Dict[str, Any]], filtered_events: List[Dict[str, Any]]) -> None:
    counts: Dict[str, int] = {}
    relevant_counts: Dict[str, int] = {}
    for event in filtered_events:
        source = str(event.get("source", "unknown"))
        counts[source] = counts.get(source, 0) + 1
        if _float(event.get("strategic_relevance_score")) >= 6.0:
            relevant_counts[source] = relevant_counts.get(source, 0) + 1
    for source, payload in sources.items():
        payload["filtered_count"] = counts.get(source, 0)
        payload["strategically_relevant_count"] = relevant_counts.get(source, 0)


def _filter_window(events: Iterable[Dict[str, Any]], now: datetime, window: timedelta) -> List[Dict[str, Any]]:
    filtered = []
    for event in events:
        timestamp = _parse_datetime(event.get("timestamp"))
        if timestamp is not None and now - window <= timestamp <= now + timedelta(minutes=5):
            filtered.append(event)
    return filtered


def _operator_note(sources: Dict[str, Dict[str, Any]], events: List[Dict[str, Any]]) -> str:
    if events:
        return "External feed context is available for BELLATOR risk evaluation."
    statuses = ", ".join(f"{source}:{payload.get('status')}" for source, payload in sorted(sources.items()))
    return f"No recent normalized feed events available. Source diagnostics: {statuses}."


def _live_enabled() -> bool:
    setting = os.getenv("BELLATOR_FEEDS_ENABLED", "auto").strip().lower()
    if setting in {"1", "true", "yes", "on", "live"}:
        return True
    if setting in {"0", "false", "no", "off", "cache", "cache_only"}:
        return False
    credential_envs = (
        "ACLED_API_KEY",
        "ACLED_KEY",
        "NASA_FIRMS_MAP_KEY",
        "FIRMS_MAP_KEY",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_RADAR_TOKEN",
    )
    return any(os.getenv(name) for name in credential_envs) or os.getenv("URLHAUS_ENABLED", "").lower() in {"1", "true", "yes", "on"}


def _disabled_result(source: str) -> Dict[str, Any]:
    return {
        "source": source,
        "ok": False,
        "status": "disabled",
        "items": [],
        "diagnostics": {"enable_with": "BELLATOR_FEEDS_ENABLED=1 or source credentials"},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _cache_path(source: str) -> Path:
    safe_name = source.replace("/", "_").replace("\\", "_")
    return FEED_CACHE_DIR / f"{safe_name}.json"


def _read_json(path: Path) -> Any:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_age_seconds(generated_at: Any) -> int | None:
    timestamp = _parse_datetime(generated_at)
    if timestamp is None:
        return None
    return max(0, int((datetime.now(timezone.utc) - timestamp).total_seconds()))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        timestamp = value
    elif value:
        try:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build BELLATOR external-feed context packets")
    parser.add_argument("--test", action="store_true", help="print a diagnostic Bellator Context Packet")
    parser.add_argument("--live", action="store_true", help="force live feed fetches for this diagnostic run")
    parser.add_argument("--cache-only", action="store_true", help="force cached/disabled diagnostics only")
    parser.add_argument("--aoi", help="apply an AOI preset or bbox filter, e.g. eastern_mediterranean")
    parser.add_argument("--countries", help="comma-separated country filter")
    parser.add_argument("--max-events", type=int, help="maximum filtered events injected into the packet")
    parser.add_argument("--min-severity", type=float, help="minimum event severity retained after normalization")
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    if not args.test:
        parser.print_help()
        return 0
    live = True if args.live else False if args.cache_only else None
    packet = build_bellator_context_packet(
        "diagnostic feed intelligence test",
        live=live,
        aoi=args.aoi,
        countries=args.countries,
        max_events=args.max_events,
        min_severity=args.min_severity,
    )
    print(json.dumps(packet, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
