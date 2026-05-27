from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .strategic_regions import resolve_strategic_region
except ImportError:
    from core.intelligence.strategic_regions import resolve_strategic_region


BBox = Tuple[float, float, float, float]
DEFAULT_MAX_EVENTS = 30
DEFAULT_MIN_SEVERITY = 4.5
STRATEGIC_RELEVANCE_THRESHOLD = 6.0


@dataclass(frozen=True)
class GeoFilterConfig:
    aoi: Optional[str] = None
    countries: Sequence[str] = field(default_factory=tuple)
    bbox: Optional[BBox] = None
    max_events: int = DEFAULT_MAX_EVENTS
    min_severity: float = DEFAULT_MIN_SEVERITY
    region: Optional[Dict[str, Any]] = None


def build_geo_filter_config(
    *,
    aoi: str | None = None,
    countries: str | Sequence[str] | None = None,
    max_events: int | str | None = None,
    min_severity: float | str | None = None,
) -> GeoFilterConfig:
    active_aoi = aoi if aoi is not None else os.getenv("BELLATOR_AOI")
    active_countries = _parse_countries(countries if countries is not None else os.getenv("BELLATOR_COUNTRIES"))
    active_max_events = _parse_int(max_events if max_events is not None else os.getenv("BELLATOR_MAX_EVENTS"), DEFAULT_MAX_EVENTS)
    active_min_severity = _parse_float(
        min_severity if min_severity is not None else os.getenv("BELLATOR_MIN_SEVERITY"),
        DEFAULT_MIN_SEVERITY,
    )
    region = resolve_strategic_region(active_aoi)
    bbox = _parse_bbox(active_aoi)
    if region and isinstance(region.get("bbox"), dict):
        bbox_payload = region["bbox"]
        bbox = (
            float(bbox_payload["lat_min"]),
            float(bbox_payload["lon_min"]),
            float(bbox_payload["lat_max"]),
            float(bbox_payload["lon_max"]),
        )
    return GeoFilterConfig(
        aoi=active_aoi,
        countries=active_countries,
        bbox=bbox,
        max_events=max(1, active_max_events),
        min_severity=max(0.0, active_min_severity),
        region=region,
    )


def filter_and_weight_events(events: Iterable[Dict[str, Any]], config: GeoFilterConfig) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    raw_events = [dict(event) for event in events]
    country_filtered = [_event for _event in raw_events if _matches_country(_event, config.countries)]
    spatial_filtered = [_event for _event in country_filtered if _matches_bbox(_event, config.bbox)]
    severity_filtered = [
        _event
        for _event in spatial_filtered
        if _is_signal_event(_event, config.min_severity)
    ]
    weighted = [_with_relevance(event, severity_filtered, config) for event in severity_filtered]
    weighted.sort(
        key=lambda event: (
            _float(event.get("strategic_relevance_score")),
            _float(event.get("severity")),
            _float(event.get("confidence")),
        ),
        reverse=True,
    )
    limited = weighted[: config.max_events]
    diagnostics = {
        "aoi": config.aoi,
        "resolved_region": config.region.get("name") if config.region else None,
        "countries": list(config.countries),
        "bbox": _bbox_dict(config.bbox),
        "min_severity": config.min_severity,
        "max_events": config.max_events,
        "raw_event_count": len(raw_events),
        "country_filtered_count": len(country_filtered),
        "spatial_filtered_count": len(spatial_filtered),
        "filtered_event_count": len(limited),
        "pre_limit_filtered_event_count": len(weighted),
        "strategically_relevant_event_count": sum(
            1 for event in limited if _float(event.get("strategic_relevance_score")) >= STRATEGIC_RELEVANCE_THRESHOLD
        ),
        "discarded_low_signal_count": len(spatial_filtered) - len(severity_filtered),
        "discarded_by_limit_count": max(0, len(weighted) - len(limited)),
    }
    return limited, diagnostics


def event_in_bbox(event: Dict[str, Any], bbox: BBox) -> bool:
    lat = _float_or_none(event.get("lat"))
    lon = _float_or_none(event.get("lon"))
    if lat is None or lon is None:
        return False
    lat_min, lon_min, lat_max, lon_max = bbox
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def strategic_relevance_score(event: Dict[str, Any], peers: Sequence[Dict[str, Any]], config: GeoFilterConfig) -> tuple[float, List[str]]:
    severity = _float(event.get("severity"))
    confidence = _float(event.get("confidence"))
    score = min(10.0, severity * max(confidence, 0.35))
    tags: List[str] = []
    region = config.region or {}
    lat = _float_or_none(event.get("lat"))
    lon = _float_or_none(event.get("lon"))
    if lat is not None and lon is not None:
        for category, bonus, radius in (
            ("ports", 2.0, 75.0),
            ("energy", 2.25, 100.0),
            ("logistics", 1.6, 90.0),
        ):
            nearest = _nearest_distance(lat, lon, region.get(category, []) or [])
            if nearest is not None and nearest <= radius:
                score += bonus
                tags.append(f"near_{category}")
            elif nearest is not None and nearest <= radius * 2:
                score += bonus / 2
                tags.append(f"near_{category}_approach")
        cluster_count = _cluster_count(event, peers, radius_km=50.0)
        if cluster_count >= 3:
            score += min(2.5, cluster_count / 2.0)
            tags.append("clustered_anomalies")
    if event.get("source") == "nasa_firms" and severity >= 7.5 and confidence >= 0.8:
        score += 0.75
        tags.append("high_confidence_thermal")
    return round(min(10.0, score), 2), sorted(set(tags))


def _with_relevance(event: Dict[str, Any], peers: Sequence[Dict[str, Any]], config: GeoFilterConfig) -> Dict[str, Any]:
    score, relevance_tags = strategic_relevance_score(event, peers, config)
    tags = list(event.get("tags", [])) if isinstance(event.get("tags"), list) else []
    event["strategic_relevance_score"] = score
    event["strategic_relevance_tags"] = relevance_tags
    event["tags"] = sorted(set([*tags, *relevance_tags]))
    return event


def _is_signal_event(event: Dict[str, Any], min_severity: float) -> bool:
    severity = _float(event.get("severity"))
    confidence = _float(event.get("confidence"))
    if severity < min_severity:
        return False
    if confidence < 0.55 and severity < max(6.0, min_severity + 1.0):
        return False
    return True


def _matches_country(event: Dict[str, Any], countries: Sequence[str]) -> bool:
    if not countries:
        return True
    country = str(event.get("country") or "").strip().lower()
    if not country:
        return False
    wanted = {item.strip().lower() for item in countries if item}
    return country in wanted


def _matches_bbox(event: Dict[str, Any], bbox: Optional[BBox]) -> bool:
    if bbox is None:
        return True
    return event_in_bbox(event, bbox)


def _cluster_count(event: Dict[str, Any], peers: Sequence[Dict[str, Any]], radius_km: float) -> int:
    lat = _float_or_none(event.get("lat"))
    lon = _float_or_none(event.get("lon"))
    if lat is None or lon is None:
        return 0
    count = 0
    for peer in peers:
        peer_lat = _float_or_none(peer.get("lat"))
        peer_lon = _float_or_none(peer.get("lon"))
        if peer_lat is None or peer_lon is None:
            continue
        if haversine_km(lat, lon, peer_lat, peer_lon) <= radius_km:
            count += 1
    return count


def _nearest_distance(lat: float, lon: float, points: Sequence[Dict[str, Any]]) -> Optional[float]:
    distances = []
    for point in points:
        point_lat = _float_or_none(point.get("lat"))
        point_lon = _float_or_none(point.get("lon"))
        if point_lat is not None and point_lon is not None:
            distances.append(haversine_km(lat, lon, point_lat, point_lon))
    return min(distances) if distances else None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_bbox(value: str | None) -> Optional[BBox]:
    if not value:
        return None
    text = value.strip()
    if text.lower().startswith("bbox:"):
        text = text.split(":", 1)[1]
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 4:
        return None
    try:
        lat_min, lon_min, lat_max, lon_max = (float(part) for part in parts)
    except ValueError:
        return None
    return (min(lat_min, lat_max), min(lon_min, lon_max), max(lat_min, lat_max), max(lon_min, lon_max))


def _parse_countries(value: str | Sequence[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    return tuple(str(part).strip() for part in value if str(part).strip())


def _parse_int(value: int | str | None, default: int) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value: float | str | None, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _bbox_dict(bbox: Optional[BBox]) -> Optional[Dict[str, float]]:
    if bbox is None:
        return None
    lat_min, lon_min, lat_max, lon_max = bbox
    return {"lat_min": lat_min, "lon_min": lon_min, "lat_max": lat_max, "lon_max": lon_max}


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "DEFAULT_MAX_EVENTS",
    "DEFAULT_MIN_SEVERITY",
    "GeoFilterConfig",
    "build_geo_filter_config",
    "event_in_bbox",
    "filter_and_weight_events",
    "haversine_km",
    "strategic_relevance_score",
]
