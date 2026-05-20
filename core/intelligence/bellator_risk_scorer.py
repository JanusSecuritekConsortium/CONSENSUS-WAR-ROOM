from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List


def score_events(events: Iterable[Dict[str, Any]], now: datetime | None = None) -> Dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    event_list = list(events)
    last_24h = [event for event in event_list if _within(event.get("timestamp"), current, timedelta(hours=24))]
    last_72h = [event for event in event_list if _within(event.get("timestamp"), current, timedelta(hours=72))]
    severities = [_float(event.get("severity")) for event in last_72h]
    confidences = [_float(event.get("confidence")) for event in last_72h]
    max_severity = max(severities, default=0.0)
    weighted_pressure = sum(severities) / max(len(severities), 1)
    event_pressure = min(len(last_72h) / 10.0, 3.0)
    score = round(min(10.0, weighted_pressure + event_pressure), 2)

    return {
        "risk_level": _risk_level(score, max_severity, len(last_24h)),
        "risk_score": score,
        "event_count": len(event_list),
        "last_24h_count": len(last_24h),
        "last_72h_count": len(last_72h),
        "max_severity": round(max_severity, 2),
        "average_confidence": round(sum(confidences) / max(len(confidences), 1), 2),
        "top_sources": _top_counts(event.get("source") for event in last_72h),
        "top_countries": _top_counts(event.get("country") for event in last_72h if event.get("country")),
        "signals": _signals(last_72h),
    }


def _risk_level(score: float, max_severity: float, last_24h_count: int) -> str:
    if max_severity >= 9.0 or score >= 8.0:
        return "SEVERE"
    if max_severity >= 7.0 or score >= 6.0 or last_24h_count >= 8:
        return "HIGH"
    if score >= 3.5 or last_24h_count >= 3:
        return "MODERATE"
    return "LOW"


def _signals(events: List[Dict[str, Any]]) -> List[str]:
    tags = Counter()
    for event in events:
        for tag in event.get("tags", []):
            tags[str(tag)] += 1
    signals = []
    for tag, count in tags.most_common(6):
        signals.append(f"{tag}:{count}")
    return signals


def _top_counts(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value)
    return dict(counter.most_common(5))


def _within(value: Any, now: datetime, window: timedelta) -> bool:
    timestamp = _parse_datetime(value)
    if timestamp is None:
        return False
    return now - window <= timestamp <= now + timedelta(minutes=5)


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
