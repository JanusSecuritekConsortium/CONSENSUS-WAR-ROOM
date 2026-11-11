"""ASCII world map: rendering, GDELT event parsing and caching, BELLATOR feed points, GUI controls."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from core.intelligence import world_events
from core.intelligence.bellator_context_builder import _compact_events
from core.intelligence.world_map import kind_runs, land_fraction, render_world_map, severity_level


def _row(root: str, lat: str, lon: str, mentions: str = "3", place: str = "Paris, France") -> list[str]:
    row = [""] * 61
    row[world_events.COL_ROOT] = root
    row[world_events.COL_MENTIONS] = mentions
    row[world_events.COL_PLACE] = place
    row[world_events.COL_COUNTRY] = "FR"
    row[world_events.COL_LAT] = lat
    row[world_events.COL_LON] = lon
    row[world_events.COL_ADDED] = "20261109093000"
    row[world_events.COL_URL] = "https://example.org/report"
    return row


def _zip(rows: list[list[str]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("x.export.CSV", "\n".join("\t".join(row) for row in rows))
    return buffer.getvalue()


def test_land_mask_knows_land_from_sea():
    assert land_fraction(49.0, 48.0, 2.0, 3.0) == 1.0  # Paris
    assert land_fraction(-30.0, -31.0, -140.0, -139.0) == 0.0  # South Pacific


def test_map_draws_land_and_strongest_marker_per_cell():
    render = render_world_map(
        [
            {"lat": 48.85, "lon": 2.35, "severity": 3, "layer": "news"},
            {"lat": 48.80, "lon": 2.30, "severity": 8, "layer": "news"},
            {"lat": 95.0, "lon": 0.0, "severity": 9},
            {"lat": "bad", "lon": 1.0},
        ],
        width=120,
        height=36,
    )
    assert render.plotted == 2 and render.skipped == 2
    assert len(render.lines) == 36 and all(len(line) == 120 for line in render.lines)
    assert sum(line.count(".") for line in render.lines) > 300
    text = "\n".join(render.lines)
    assert text.count("#") == 1 and "+" not in text


def test_bellator_feed_event_wins_a_tie_with_news():
    render = render_world_map(
        [{"lat": 10.0, "lon": 10.0, "severity": 8, "layer": "news"},
         {"lat": 10.0, "lon": 10.0, "severity": 8, "layer": "feed"}],
        width=60, height=20,
    )
    assert "X" in "".join(render.lines) and "#" not in "".join(render.lines)


def test_regions_are_outlined():
    region = {"bbox": {"lat_min": 30.0, "lat_max": 42.5, "lon_min": 19.0, "lon_max": 37.5}}
    render = render_world_map([], width=120, height=36, regions=[region])
    assert sum(kinds.count("r") for kinds in render.kinds) > 8


def test_severity_levels_and_runs():
    assert [severity_level(v) for v in (None, 4.9, 5, 7)] == ["1", "1", "2", "3"]
    assert kind_runs("ab  c", "ll  3") == [("ab", "l"), ("  ", " "), ("c", "3")]


def test_gdelt_rows_keep_conflict_events_and_merge_duplicates():
    events = world_events.parse_export_rows([
        _row("19", "48.85", "2.35", mentions="2"),
        _row("19", "48.86", "2.35", mentions="12"),  # same place and type: kept once, with more mentions
        _row("03", "40.0", "3.0"),  # cooperation: not shown
        _row("14", "", "3.0"),  # no coordinates
        _row("14", "51.5", "-0.12"),
    ])
    assert [event["event_type"] for event in events] == ["fighting", "protest"]
    assert events[0]["mentions"] == 12 and events[0]["severity"] == 9.0
    assert events[0]["timestamp"].startswith("2026-11-09T09:30:00")


def test_fetch_reads_the_last_hour_of_files():
    requested = []

    def opener(url: str, timeout: int) -> bytes:
        requested.append(url.rsplit("/", 1)[-1])
        if url.endswith("lastupdate.txt"):
            return b"1 a http://data.gdeltproject.org/gdeltv2/20261109093000.export.CSV.zip\n"
        if "20261109090000" in url:
            raise OSError("missing file")
        return _zip([_row("18", "10.0", "20.0")])

    result = world_events.fetch_gdelt_events(files=4, opener=opener)
    assert result["ok"] and result["diagnostics"]["failed_files"] == 1
    assert requested[1:] == ["20261109093000.export.CSV.zip", "20261109091500.export.CSV.zip",
                             "20261109090000.export.CSV.zip", "20261109084500.export.CSV.zip"]
    assert len(result["items"]) == 1  # identical events in three files merge into one


def test_fetch_reports_network_failure():
    def opener(url: str, timeout: int) -> bytes:
        raise OSError("offline")

    result = world_events.fetch_gdelt_events(opener=opener)
    assert not result["ok"] and result["status"] == "network_error"


@pytest.fixture
def gdelt_on(monkeypatch):
    monkeypatch.setenv("BELLATOR_GDELT_EVENTS", "1")
    monkeypatch.delenv("BELLATOR_FEEDS_ENABLED", raising=False)


def test_cache_is_reused_for_15_minutes(tmp_path, gdelt_on):
    now = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)
    cache = tmp_path / "gdelt.json"
    calls = []

    def fetcher():
        calls.append(1)
        return {"ok": True, "status": "ok", "items": [{"lat": 1, "lon": 1}], "fetched_at": now.isoformat()}

    world_events.load_gdelt_events(live=True, now=now, cache_path=cache, fetcher=fetcher)
    world_events.load_gdelt_events(live=True, now=now + timedelta(minutes=10), cache_path=cache, fetcher=fetcher)
    assert len(calls) == 1
    world_events.load_gdelt_events(live=True, now=now + timedelta(minutes=20), cache_path=cache, fetcher=fetcher)
    assert len(calls) == 2
    assert world_events.load_gdelt_events(live=False, now=now + timedelta(days=1), cache_path=cache,
                                          fetcher=fetcher)["items"]
    assert len(calls) == 2


def test_failed_refresh_keeps_the_old_events(tmp_path, gdelt_on):
    cache = tmp_path / "gdelt.json"
    cache.write_text(json.dumps({"ok": True, "status": "ok", "items": [{"lat": 1, "lon": 1}],
                                 "fetched_at": "2026-11-09T08:00:00+00:00"}), encoding="utf-8")
    result = world_events.load_gdelt_events(
        live=True, now=datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc), cache_path=cache,
        fetcher=lambda: {"ok": False, "status": "network_error", "items": [], "diagnostics": {"error": "x"}})
    assert result["status"] == "stale" and result["items"]


def test_download_can_be_turned_off(tmp_path, monkeypatch):
    monkeypatch.setenv("BELLATOR_GDELT_EVENTS", "0")
    result = world_events.load_gdelt_events(live=True, cache_path=tmp_path / "x.json",
                                            fetcher=lambda: pytest.fail("must not fetch"))
    assert result["status"] == "disabled"


def test_bellator_packet_events_keep_coordinates_for_the_map(tmp_path):
    compact = _compact_events([{"source": "acled", "lat": 34.7, "lon": 33.0, "severity": 7,
                                "timestamp": "2026-11-09T09:00:00+00:00"}], 5)
    assert compact[0]["lat"] == 34.7 and compact[0]["lon"] == 33.0
    packet = tmp_path / "packet.json"
    packet.write_text(json.dumps({"events": compact + [{"source": "x", "lat": None, "lon": 1}]}), encoding="utf-8")
    points = world_events.bellator_feed_points(packet)
    assert len(points) == 1 and points[0]["layer"] == "feed"


def test_gui_controls_build():
    from ui.components.world_map_view import build_mini_map, build_world_map_overlay, map_status_line
    from tests.helpers.gui_harness import make_gui_state

    theme = make_gui_state("janus").theme
    data = {"points": [{"lat": 48.85, "lon": 2.35, "severity": 8, "layer": "news", "place": "Paris"}],
            "feed_count": 0, "news_count": 1, "news_status": "ok", "news_fetched_at": "2026-11-09T09:45:00+00:00"}
    mini = build_mini_map(theme, data)
    assert mini.data == {"role": "world_mini_map"}
    overlay = build_world_map_overlay(theme, data, busy=False, page_width=1600)
    assert overlay.data == {"role": "world_map_overlay"}
    assert "1 GDELT" in map_status_line(data) and "not loaded" in map_status_line({})


def test_map_land_stays_readable_on_every_theme():
    from ui.components.world_map_view import LAND_FALLBACK, MIN_LAND_CONTRAST, contrast, land_colour
    from ui.themes.catalog import THEMES
    for key, theme in THEMES.items():
        colour = land_colour(theme)
        assert contrast(colour, theme.background_color) >= MIN_LAND_CONTRAST, key
    assert land_colour(THEMES["arasaka"]) == LAND_FALLBACK  # its secondary colour is near-black
    assert land_colour(THEMES["military"]) == THEMES["military"].secondary_color
