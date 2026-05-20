from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SOURCE = "nasa_firms"
DEFAULT_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def fetch_nasa_firms_events(days: int = 3, timeout: int = 8) -> Dict[str, Any]:
    map_key = os.getenv("NASA_FIRMS_MAP_KEY") or os.getenv("FIRMS_MAP_KEY")
    base_url = os.getenv("NASA_FIRMS_BASE_URL", DEFAULT_BASE_URL)
    satellite_source = os.getenv("NASA_FIRMS_SOURCE", "VIIRS_SNPP_NRT")
    fetched_at = datetime.now(timezone.utc).isoformat()

    if not map_key:
        return _result(False, "missing_api_key", [], fetched_at, {"requires": ["NASA_FIRMS_MAP_KEY"]})

    url = f"{base_url}/{map_key}/{satellite_source}/world/{max(days, 1)}"
    try:
        request = Request(url, headers={"Accept": "text/csv", "User-Agent": "CONSENSUS-BELLATOR/7.9"})
        with urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
        items = list(csv.DictReader(StringIO(text)))
    except HTTPError as exc:
        return _result(False, "http_error", [], fetched_at, {"code": exc.code, "reason": exc.reason})
    except (URLError, TimeoutError, OSError) as exc:
        return _result(False, "network_error", [], fetched_at, {"error": str(exc)})
    except Exception as exc:
        return _result(False, "parse_error", [], fetched_at, {"error": str(exc)})

    return _result(True, "ok", items, fetched_at, {"count": len(items), "satellite_source": satellite_source})


def _result(ok: bool, status: str, items: list[Dict[str, Any]], fetched_at: str, diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": SOURCE,
        "ok": ok,
        "status": status,
        "items": items,
        "diagnostics": diagnostics,
        "fetched_at": fetched_at,
    }
