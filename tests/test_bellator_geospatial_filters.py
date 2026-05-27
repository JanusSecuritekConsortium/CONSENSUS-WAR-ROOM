from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core.intelligence.bellator_context_builder as context_builder
from core.intelligence.geospatial_filters import build_geo_filter_config, filter_and_weight_events
from core.intelligence.strategic_regions import resolve_strategic_region


def _event(lat: float, lon: float, severity: float, confidence: float = 0.9, source: str = "nasa_firms"):
    return {
        "source": source,
        "event_type": "thermal_anomaly",
        "country": None,
        "region": None,
        "lat": lat,
        "lon": lon,
        "timestamp": "2026-05-19T08:00:00+00:00",
        "severity": severity,
        "confidence": confidence,
        "summary": "test anomaly",
        "tags": ["fire", "thermal_anomaly"],
    }


def test_strategic_presets_resolve() -> None:
    region = resolve_strategic_region("eastern_mediterranean")

    assert region is not None
    assert region["name"] == "eastern_mediterranean"
    assert region["bbox"]["lat_min"] < 34.7 < region["bbox"]["lat_max"]
    assert region["bbox"]["lon_min"] < 33.0 < region["bbox"]["lon_max"]


def test_aoi_filtering_works() -> None:
    config = build_geo_filter_config(aoi="eastern_mediterranean", max_events=10, min_severity=4.0)
    filtered, diagnostics = filter_and_weight_events(
        [
            _event(34.7, 33.0, 7.5),
            _event(50.0, 50.0, 9.0),
        ],
        config,
    )

    assert len(filtered) == 1
    assert filtered[0]["lat"] == 34.7
    assert diagnostics["raw_event_count"] == 2
    assert diagnostics["spatial_filtered_count"] == 1


def test_low_severity_events_are_excluded() -> None:
    config = build_geo_filter_config(aoi="eastern_mediterranean", max_events=10, min_severity=5.0)
    filtered, diagnostics = filter_and_weight_events(
        [
            _event(34.7, 33.0, 4.0, confidence=0.9),
            _event(34.8, 33.1, 7.0, confidence=0.9),
        ],
        config,
    )

    assert len(filtered) == 1
    assert filtered[0]["severity"] == 7.0
    assert diagnostics["discarded_low_signal_count"] == 1


def test_bellator_packet_reports_filtered_counts() -> None:
    previous_env = {
        "BELLATOR_AOI": os.environ.get("BELLATOR_AOI"),
        "BELLATOR_MAX_EVENTS": os.environ.get("BELLATOR_MAX_EVENTS"),
        "BELLATOR_MIN_SEVERITY": os.environ.get("BELLATOR_MIN_SEVERITY"),
    }
    original_collect = context_builder._collect_feed_results
    try:
        for key in previous_env:
            os.environ.pop(key, None)

        context_builder._collect_feed_results = lambda live: [
            {
                "source": "nasa_firms",
                "ok": True,
                "status": "ok",
                "items": [
                    {"latitude": "34.7", "longitude": "33.0", "acq_date": "2026-05-19", "acq_time": "0800", "frp": "160", "confidence": "h"},
                    {"latitude": "34.8", "longitude": "33.1", "acq_date": "2026-05-19", "acq_time": "0810", "frp": "0", "confidence": "l"},
                    {"latitude": "50.0", "longitude": "50.0", "acq_date": "2026-05-19", "acq_time": "0820", "frp": "200", "confidence": "h"},
                ],
                "diagnostics": {},
                "fetched_at": "2026-05-19T08:30:00+00:00",
            }
        ]

        packet = context_builder.build_bellator_context_packet(
            "geospatial packet test",
            live=True,
            now=datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc),
            aoi="eastern_mediterranean",
            max_events=5,
            min_severity=5.0,
        )

        assert packet["feed_counts"]["raw_event_count"] == 3
        assert packet["feed_counts"]["recent_72h_raw_event_count"] == 3
        assert packet["feed_counts"]["filtered_event_count"] == 1
        assert packet["feed_counts"]["strategically_relevant_event_count"] == 1
        assert packet["filters"]["resolved_region"] == "eastern_mediterranean"
        assert packet["sources"]["nasa_firms"]["filtered_count"] == 1
        assert packet["events"][0]["strategic_relevance_score"] >= 6.0
    finally:
        context_builder._collect_feed_results = original_collect
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    test_strategic_presets_resolve()
    test_aoi_filtering_works()
    test_low_severity_events_are_excluded()
    test_bellator_packet_reports_filtered_counts()
    print("test_bellator_geospatial_filters PASS")
