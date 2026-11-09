"""World map events: free GDELT news events plus BELLATOR's own feed events.

GDELT (gdeltproject.org) publishes machine-coded news events every 15 minutes with coordinates and
needs no key. These events feed only the world map: they are not added to BELLATOR's prompt or risk
score. Turn the download off with BELLATOR_GDELT_EVENTS=0 (BELLATOR_FEEDS_ENABLED=0 also stops it).
"""
from __future__ import annotations

import csv
import io
import json
import os
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.request import Request, urlopen

from core.intelligence.bellator_context_builder import FEED_CACHE_DIR, PACKET_CACHE_PATH

SOURCE = "gdelt_events"
GDELT_BASE_URL = "https://data.gdeltproject.org/gdeltv2"
CACHE_PATH = FEED_CACHE_DIR / "gdelt_world_events.json"
CACHE_MAX_AGE_SECONDS = 15 * 60
FILES_PER_FETCH = 4  # one file per 15 minutes, so the last hour
MAX_EVENTS = 600
USER_AGENT = "CONSENSUS-BELLATOR-map"
OFF_VALUES = {"0", "false", "no", "off", "cache", "cache_only"}

# CAMEO root codes worth showing, with a base severity on BELLATOR's 1-10 scale.
CONFLICT_ROOTS = {
    "14": ("protest", 4.0),
    "15": ("show of force", 5.0),
    "17": ("coercion", 5.0),
    "18": ("assault", 7.0),
    "19": ("fighting", 8.0),
    "20": ("mass violence", 9.0),
}
# GDELT 2.0 export column positions.
COL_ROOT, COL_MENTIONS = 28, 31
COL_PLACE, COL_COUNTRY, COL_LAT, COL_LON = 52, 53, 56, 57
COL_ADDED, COL_URL = 59, 60

Opener = Callable[[str, int], bytes]


def gdelt_enabled() -> bool:
    if os.getenv("BELLATOR_FEEDS_ENABLED", "auto").strip().lower() in OFF_VALUES:
        return False
    return os.getenv("BELLATOR_GDELT_EVENTS", "1").strip().lower() not in OFF_VALUES


def _download(url: str, timeout: int) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _latest_stamp(opener: Opener, timeout: int) -> str:
    text = opener(f"{GDELT_BASE_URL}/lastupdate.txt", timeout).decode("utf-8", errors="replace")
    for line in text.splitlines():
        url = line.strip().split(" ")[-1]
        if url.endswith(".export.CSV.zip"):
            return url.rsplit("/", 1)[-1].split(".", 1)[0]
    raise ValueError("lastupdate.txt lists no export file")


def parse_export_rows(rows: List[List[str]]) -> List[Dict[str, Any]]:
    events: Dict[tuple, Dict[str, Any]] = {}
    for row in rows:
        if len(row) <= COL_URL or row[COL_ROOT] not in CONFLICT_ROOTS:
            continue
        try:
            lat, lon = float(row[COL_LAT]), float(row[COL_LON])
        except ValueError:
            continue
        label, base = CONFLICT_ROOTS[row[COL_ROOT]]
        try:
            mentions = int(row[COL_MENTIONS])
        except ValueError:
            mentions = 1
        severity = min(10.0, base + (1.0 if mentions >= 10 else 0.0))
        added = row[COL_ADDED]
        try:
            timestamp = datetime.strptime(added, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            timestamp = ""
        key = (round(lat, 1), round(lon, 1), row[COL_ROOT])
        event = {
            "layer": "news",
            "source": SOURCE,
            "event_type": label,
            "place": row[COL_PLACE],
            "country_code": row[COL_COUNTRY],
            "lat": lat,
            "lon": lon,
            "severity": severity,
            "mentions": mentions,
            "timestamp": timestamp,
            "url": row[COL_URL],
        }
        if key not in events or mentions > events[key]["mentions"]:
            events[key] = event
    return sorted(events.values(), key=lambda item: (item["severity"], item["mentions"]), reverse=True)


def fetch_gdelt_events(files: int = FILES_PER_FETCH, timeout: int = 10, opener: Opener = _download) -> Dict[str, Any]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        latest = datetime.strptime(_latest_stamp(opener, timeout), "%Y%m%d%H%M%S")
    except Exception as exc:
        return {"source": SOURCE, "ok": False, "status": "network_error", "items": [], "fetched_at": fetched_at,
                "diagnostics": {"error": f"{type(exc).__name__}: {exc}"}}
    rows: List[List[str]] = []
    failures = 0
    for step in range(max(1, files)):
        stamp = (latest - timedelta(minutes=15 * step)).strftime("%Y%m%d%H%M%S")
        try:
            archive = zipfile.ZipFile(io.BytesIO(opener(f"{GDELT_BASE_URL}/{stamp}.export.CSV.zip", timeout)))
            with archive.open(archive.namelist()[0]) as handle:
                text = io.TextIOWrapper(handle, encoding="utf-8", errors="replace")
                rows.extend(csv.reader(text, delimiter="\t"))
        except Exception:
            failures += 1
    if failures == max(1, files):
        return {"source": SOURCE, "ok": False, "status": "network_error", "items": [], "fetched_at": fetched_at,
                "diagnostics": {"error": "no GDELT export file could be read"}}
    items = parse_export_rows(rows)[:MAX_EVENTS]
    return {"source": SOURCE, "ok": True, "status": "ok", "items": items, "fetched_at": fetched_at,
            "diagnostics": {"files": files, "failed_files": failures, "rows": len(rows), "latest": latest.isoformat()}}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


def _age_seconds(value: Any, now: datetime) -> Optional[float]:
    try:
        moment = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (now - moment).total_seconds()


def load_gdelt_events(*, live: bool, now: datetime | None = None, cache_path: Path = CACHE_PATH,
                      fetcher: Callable[[], Dict[str, Any]] = fetch_gdelt_events) -> Dict[str, Any]:
    """Cached GDELT events; with live=True, fetch again once the cache is older than 15 minutes."""
    current = now or datetime.now(timezone.utc)
    cached = _read_json(cache_path)
    if not gdelt_enabled():
        return {"source": SOURCE, "ok": False, "status": "disabled", "items": [],
                "diagnostics": {"enable_with": "BELLATOR_GDELT_EVENTS=1"}}
    age = _age_seconds(cached.get("fetched_at"), current) if isinstance(cached, dict) else None
    if live and (age is None or age > CACHE_MAX_AGE_SECONDS):
        result = fetcher()
        if result.get("ok") or not isinstance(cached, dict):
            _write_json(cache_path, result)
            return result
        cached = dict(cached, status="stale", diagnostics={"refresh_error": result.get("diagnostics")})
    if isinstance(cached, dict):
        return cached
    return {"source": SOURCE, "ok": False, "status": "not_fetched", "items": [], "diagnostics": {}}


def bellator_feed_points(packet_path: Path = PACKET_CACHE_PATH) -> List[Dict[str, Any]]:
    packet = _read_json(packet_path)
    events = packet.get("events", []) if isinstance(packet, dict) else []
    points = []
    for event in events:
        if not isinstance(event, dict) or event.get("lat") is None or event.get("lon") is None:
            continue
        points.append({
            "layer": "feed",
            "source": event.get("source"),
            "event_type": event.get("event_type"),
            "place": event.get("region") or event.get("country") or "",
            "lat": event.get("lat"),
            "lon": event.get("lon"),
            "severity": event.get("severity"),
            "timestamp": event.get("timestamp"),
            "summary": event.get("summary"),
        })
    return points


def build_world_map_points(*, live: bool, now: datetime | None = None) -> Dict[str, Any]:
    """Everything the map shows: BELLATOR's own feed events first, then GDELT news events."""
    gdelt = load_gdelt_events(live=live, now=now)
    feed = bellator_feed_points()
    return {
        "points": feed + list(gdelt.get("items") or []),
        "feed_count": len(feed),
        "news_count": len(gdelt.get("items") or []),
        "news_status": gdelt.get("status", "unknown"),
        "news_fetched_at": gdelt.get("fetched_at"),
    }
