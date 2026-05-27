from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.intelligence.bellator_context_builder import (
    ANTI_FABRICATION_INSTRUCTION,
    build_bellator_context_packet,
    build_bellator_diagnostics_payload,
)
from config.version import SYSTEM_VERSION
from core.intelligence.bellator_feed_normalizer import normalize_feed_result
from core.intelligence.bellator_risk_scorer import score_events
from integrations.feeds.abuse_ch_client import fetch_urlhaus_recent


REQUIRED_SCHEMA = {
    "source",
    "event_type",
    "country",
    "region",
    "lat",
    "lon",
    "timestamp",
    "severity",
    "confidence",
    "summary",
    "tags",
}

FEED_ENV_KEYS = (
    "ACLED_API_KEY",
    "ACLED_KEY",
    "ACLED_EMAIL",
    "ACLED_PASSWORD",
    "ACLED_ACCESS_TOKEN",
    "ACLED_ENABLE_LEGACY_KEY",
    "NASA_FIRMS_MAP_KEY",
    "FIRMS_MAP_KEY",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_RADAR_TOKEN",
    "URLHAUS_ENABLED",
    "URLHAUS_AUTH_KEY",
    "BELLATOR_FEEDS_ENABLED",
)


def test_feed_normalizer_emits_shared_schema() -> None:
    events = normalize_feed_result(
        {
            "source": "acled",
            "ok": True,
            "status": "ok",
            "items": [
                {
                    "event_type": "Protests",
                    "sub_event_type": "Peaceful protest",
                    "country": "Exampleland",
                    "admin1": "North",
                    "latitude": "10.5",
                    "longitude": "-66.9",
                    "event_date": "2026-05-19",
                    "fatalities": "0",
                    "notes": "Dummy protest record.",
                }
            ],
        }
    )

    assert len(events) == 1
    assert REQUIRED_SCHEMA <= set(events[0])
    assert events[0]["source"] == "acled"
    assert events[0]["event_type"] == "Protests"


def test_risk_scorer_builds_compact_summary() -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    events = normalize_feed_result(
        {
            "source": "nasa_firms",
            "ok": True,
            "status": "ok",
            "items": [
                {
                    "latitude": "12.1",
                    "longitude": "13.2",
                    "acq_date": today,
                    "acq_time": "0800",
                    "frp": "120",
                    "confidence": "h",
                }
            ],
        }
    )

    score = score_events(events)

    assert score["event_count"] == 1
    assert score["last_72h_count"] == 1
    assert score["risk_level"] in {"LOW", "MODERATE", "HIGH", "SEVERE"}


def test_context_builder_cache_only_packet() -> None:
    os.environ["BELLATOR_FEEDS_ENABLED"] = "0"

    packet = build_bellator_context_packet("dummy tactical vote", live=False)

    assert packet["label"] == "BELLATOR CONTEXT PACKET"
    assert packet["version"] == SYSTEM_VERSION
    assert packet["mode"] == "cache_only"
    assert packet["anti_fabrication_instruction"] == ANTI_FABRICATION_INSTRUCTION
    assert "risk" in packet
    assert "sources" in packet
    assert Path(packet["cache_dir"]).exists()


def test_live_packet_without_credentials_returns_diagnostics() -> None:
    previous = {key: os.environ.get(key) for key in FEED_ENV_KEYS}
    try:
        for key in FEED_ENV_KEYS:
            os.environ.pop(key, None)

        packet = build_bellator_context_packet("empty credential diagnostic", live=True)

        assert packet["label"] == "BELLATOR CONTEXT PACKET"
        assert packet["mode"] == "live"
        assert packet["sources"]["acled"]["status"] == "missing_credentials"
        assert packet["sources"]["nasa_firms"]["status"] == "missing_api_key"
        assert packet["sources"]["cloudflare_radar"]["status"] == "missing_api_key"
        assert packet["sources"]["abuse_ch_urlhaus"]["status"] == "disabled"

        diagnostics = build_bellator_diagnostics_payload(packet)

        assert diagnostics["available"] is True
        assert diagnostics["normalized_event_count"] == 0
        assert "acled:missing_credentials" in diagnostics["source_diagnostics_summary"]
        assert "abuse_ch_urlhaus:disabled" in diagnostics["source_diagnostics_summary"]
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_urlhaus_requires_explicit_opt_in() -> None:
    previous_enabled = os.environ.get("URLHAUS_ENABLED")
    previous_key = os.environ.get("URLHAUS_AUTH_KEY")
    try:
        os.environ.pop("URLHAUS_ENABLED", None)
        os.environ["URLHAUS_AUTH_KEY"] = "dummy-key-does-not-enable-network"

        result = fetch_urlhaus_recent()

        assert result["status"] == "disabled"
        assert result["items"] == []
    finally:
        if previous_enabled is None:
            os.environ.pop("URLHAUS_ENABLED", None)
        else:
            os.environ["URLHAUS_ENABLED"] = previous_enabled
        if previous_key is None:
            os.environ.pop("URLHAUS_AUTH_KEY", None)
        else:
            os.environ["URLHAUS_AUTH_KEY"] = previous_key


if __name__ == "__main__":
    test_feed_normalizer_emits_shared_schema()
    test_risk_scorer_builds_compact_summary()
    test_context_builder_cache_only_packet()
    test_live_packet_without_credentials_returns_diagnostics()
    test_urlhaus_requires_explicit_opt_in()
    print("test_bellator_feed_intelligence PASS")
