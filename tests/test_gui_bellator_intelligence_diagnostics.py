from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.intelligence.bellator_context_builder import build_bellator_diagnostics_payload
from ui.components.bellator_intelligence_panel import format_bellator_intelligence_diagnostics


def test_diagnostics_payload_handles_empty_sources() -> None:
    payload = build_bellator_diagnostics_payload(
        {
            "generated_at": "2026-05-19T12:00:00+00:00",
            "sources": {},
            "risk": {"max_severity": 0.0},
        }
    )

    assert payload["available"] is True
    assert payload["enabled_sources"] == []
    assert payload["unavailable_sources"] == []
    assert payload["normalized_event_count"] == 0
    assert payload["highest_severity"] == 0.0


def test_gui_formatter_handles_missing_sources() -> None:
    lines = format_bellator_intelligence_diagnostics(
        {
            "available": True,
            "timestamp": "2026-05-19T12:00:00+00:00",
            "enabled_sources": [],
            "unavailable_sources": ["acled:missing_api_key", "abuse_ch_urlhaus:disabled"],
            "cache_age_seconds": 90,
            "normalized_event_count": 0,
            "highest_severity": 0.0,
            "source_diagnostics_summary": "acled:missing_api_key, abuse_ch_urlhaus:disabled",
        }
    )

    text = "\n".join(lines)
    assert "PACKET: 2026-05-19T12:00:00+00:00" in text
    assert "ENABLED: none" in text
    assert "UNAVAILABLE: acled:missing_api_key, abuse_ch_urlhaus:disabled" in text
    assert "CACHE AGE: 1m" in text
    assert "NORMALIZED EVENTS: 0" in text
    assert "HIGHEST SEVERITY: 0.0" in text


def test_gui_formatter_handles_unavailable_packet() -> None:
    lines = format_bellator_intelligence_diagnostics(None)

    assert lines[0] == "PACKET: unavailable"
    assert "No Bellator Context Packet cache found." in lines[1]


if __name__ == "__main__":
    test_diagnostics_payload_handles_empty_sources()
    test_gui_formatter_handles_missing_sources()
    test_gui_formatter_handles_unavailable_packet()
    print("test_gui_bellator_intelligence_diagnostics PASS")
