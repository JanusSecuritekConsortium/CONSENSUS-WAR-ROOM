from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class BellatorFeedEvent:
    source: str
    event_type: str
    country: Optional[str]
    region: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    timestamp: str
    severity: float
    confidence: float
    summary: str
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_feed_result(feed_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    source = feed_result.get("source")
    items = feed_result.get("items", [])
    if not isinstance(items, list):
        return []
    if source == "acled":
        events = normalize_acled(items)
    elif source == "nasa_firms":
        events = normalize_nasa_firms(items)
    elif source == "cloudflare_radar":
        events = normalize_cloudflare_radar(items)
    elif source == "abuse_ch_urlhaus":
        events = normalize_abuse_ch(items)
    else:
        events = []
    return [event.to_dict() for event in events]


def normalize_acled(items: Iterable[Dict[str, Any]]) -> List[BellatorFeedEvent]:
    events: List[BellatorFeedEvent] = []
    for item in items:
        event_type = str(item.get("event_type") or item.get("disorder_type") or "conflict_event")
        sub_event_type = str(item.get("sub_event_type") or "").strip()
        fatalities = _float_or_none(item.get("fatalities")) or 0.0
        severity = _clamp(3.0 + min(fatalities, 7.0), 1.0, 10.0)
        if "battle" in event_type.lower() or "explosion" in event_type.lower() or "violence" in event_type.lower():
            severity = max(severity, 7.0)
        elif "protest" in event_type.lower():
            severity = max(severity, 4.0)
        summary_parts = [
            item.get("event_type") or "ACLED event",
            item.get("sub_event_type"),
            item.get("location"),
            item.get("notes"),
        ]
        tags = ["conflict", "acled"]
        if sub_event_type:
            tags.append(_slug(sub_event_type))
        events.append(
            BellatorFeedEvent(
                source="acled",
                event_type=event_type,
                country=_text_or_none(item.get("country")),
                region=_text_or_none(item.get("admin1") or item.get("region")),
                lat=_float_or_none(item.get("latitude")),
                lon=_float_or_none(item.get("longitude")),
                timestamp=_parse_timestamp(item.get("event_date") or item.get("timestamp")),
                severity=severity,
                confidence=0.82,
                summary=_summary(summary_parts, 260),
                tags=tags,
            )
        )
    return events


def normalize_nasa_firms(items: Iterable[Dict[str, Any]]) -> List[BellatorFeedEvent]:
    events: List[BellatorFeedEvent] = []
    for item in items:
        brightness = _float_or_none(item.get("bright_ti4") or item.get("brightness") or item.get("bright_t31"))
        frp = _float_or_none(item.get("frp")) or 0.0
        confidence = _firms_confidence(item.get("confidence"))
        severity = _clamp(4.0 + min(frp / 80.0, 4.0) + (1.5 if confidence >= 0.8 else 0.0), 1.0, 10.0)
        acquired = _combine_date_time(item.get("acq_date"), item.get("acq_time"))
        tags = ["fire", "thermal_anomaly", "nasa_firms"]
        if item.get("satellite"):
            tags.append(_slug(item["satellite"]))
        summary = _summary(
            [
                "Thermal anomaly detected",
                f"brightness={brightness}" if brightness is not None else None,
                f"frp={frp}" if frp else None,
                f"confidence={item.get('confidence')}" if item.get("confidence") is not None else None,
            ],
            220,
        )
        events.append(
            BellatorFeedEvent(
                source="nasa_firms",
                event_type="thermal_anomaly",
                country=_text_or_none(item.get("country_id") or item.get("country")),
                region=_text_or_none(item.get("region")),
                lat=_float_or_none(item.get("latitude")),
                lon=_float_or_none(item.get("longitude")),
                timestamp=acquired,
                severity=severity,
                confidence=confidence,
                summary=summary,
                tags=tags,
            )
        )
    return events


def normalize_cloudflare_radar(items: Iterable[Dict[str, Any]]) -> List[BellatorFeedEvent]:
    events: List[BellatorFeedEvent] = []
    for item in items:
        event_type = str(item.get("eventType") or item.get("event_type") or item.get("type") or "internet_outage")
        start_time = item.get("startDate") or item.get("start_time") or item.get("date") or item.get("timestamp")
        country = item.get("country") or item.get("countryName") or item.get("locationName")
        region = item.get("region") or item.get("asnName") or item.get("location")
        confidence = _cloudflare_confidence(item.get("confidence"))
        severity = _clamp(6.0 + (2.0 if "outage" in event_type.lower() else 0.0) + confidence, 1.0, 10.0)
        tags = ["internet_disruption", "cloudflare_radar", _slug(event_type)]
        events.append(
            BellatorFeedEvent(
                source="cloudflare_radar",
                event_type=event_type,
                country=_text_or_none(country),
                region=_text_or_none(region),
                lat=_float_or_none(item.get("lat") or item.get("latitude")),
                lon=_float_or_none(item.get("lon") or item.get("longitude")),
                timestamp=_parse_timestamp(start_time),
                severity=severity,
                confidence=confidence,
                summary=_summary([item.get("description"), item.get("name"), item.get("message"), event_type], 240),
                tags=[tag for tag in tags if tag],
            )
        )
    return events


def normalize_abuse_ch(items: Iterable[Dict[str, Any]]) -> List[BellatorFeedEvent]:
    events: List[BellatorFeedEvent] = []
    for item in items:
        threat = str(item.get("threat") or item.get("tags") or item.get("url_status") or "malicious_url")
        tags = ["ioc", "urlhaus", "malware_url"]
        item_tags = item.get("tags")
        if isinstance(item_tags, list):
            tags.extend(_slug(tag) for tag in item_tags if tag)
        elif isinstance(item_tags, str):
            tags.append(_slug(item_tags))
        events.append(
            BellatorFeedEvent(
                source="abuse_ch_urlhaus",
                event_type="ioc_url",
                country=_text_or_none(item.get("country")),
                region=_text_or_none(item.get("host") or item.get("urlhaus_reference")),
                lat=None,
                lon=None,
                timestamp=_parse_timestamp(item.get("date_added") or item.get("firstseen") or item.get("timestamp")),
                severity=7.0 if item.get("url_status") != "offline" else 5.0,
                confidence=0.84,
                summary=_summary([threat, item.get("url"), item.get("urlhaus_reference")], 260),
                tags=sorted(set(tag for tag in tags if tag)),
            )
        )
    return events


def event_to_dict(event: BellatorFeedEvent) -> Dict[str, Any]:
    return event.to_dict()


def _parse_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        timestamp = value
    elif value:
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                timestamp = datetime.strptime(text, fmt)
                break
            except ValueError:
                timestamp = None  # type: ignore[assignment]
        else:
            try:
                timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now(timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat()


def _combine_date_time(date_value: Any, time_value: Any) -> str:
    if not date_value:
        return _parse_timestamp(None)
    date_text = str(date_value)
    time_text = str(time_value or "0000").zfill(4)
    return _parse_timestamp(f"{date_text} {time_text[:2]}:{time_text[2:]}:00")


def _firms_confidence(value: Any) -> float:
    if value is None:
        return 0.7
    text = str(value).strip().lower()
    if text in {"l", "low"}:
        return 0.45
    if text in {"n", "nominal", "m", "medium"}:
        return 0.7
    if text in {"h", "high"}:
        return 0.9
    numeric = _float_or_none(value)
    if numeric is None:
        return 0.7
    return _clamp(numeric / 100.0 if numeric > 1 else numeric, 0.0, 1.0)


def _cloudflare_confidence(value: Any) -> float:
    numeric = _float_or_none(value)
    if numeric is not None:
        return _clamp(numeric / 100.0 if numeric > 1 else numeric, 0.0, 1.0)
    text = str(value or "").lower()
    if "high" in text:
        return 0.9
    if "low" in text:
        return 0.45
    return 0.72


def _float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _text_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _summary(parts: Iterable[Any], max_len: int) -> str:
    text = " | ".join(str(part).strip() for part in parts if part is not None and str(part).strip())
    if len(text) > max_len:
        return text[: max_len - 3].rstrip() + "..."
    return text or "External risk signal."


def _slug(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("/", "_")


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
