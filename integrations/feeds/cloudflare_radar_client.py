from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SOURCE = "cloudflare_radar"
DEFAULT_BASE_URL = "https://api.cloudflare.com/client/v4/radar/annotations/outages"


def fetch_cloudflare_outages(days: int = 3, limit: int = 100, timeout: int = 8) -> Dict[str, Any]:
    token = os.getenv("CLOUDFLARE_API_TOKEN") or os.getenv("CLOUDFLARE_RADAR_TOKEN")
    base_url = os.getenv("CLOUDFLARE_RADAR_BASE_URL", DEFAULT_BASE_URL)
    fetched_at = datetime.now(timezone.utc).isoformat()

    if not token:
        return _result(False, "missing_api_key", [], fetched_at, {"requires": ["CLOUDFLARE_API_TOKEN"]})

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=max(days, 1))
    params = {
        "dateStart": start_time.isoformat().replace("+00:00", "Z"),
        "dateEnd": end_time.isoformat().replace("+00:00", "Z"),
        "limit": str(limit),
    }
    url = f"{base_url}?{urlencode(params)}"
    try:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "CONSENSUS-BELLATOR/7.9",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return _result(False, "http_error", [], fetched_at, {"code": exc.code, "reason": exc.reason})
    except (URLError, TimeoutError, OSError) as exc:
        return _result(False, "network_error", [], fetched_at, {"error": str(exc)})
    except Exception as exc:
        return _result(False, "parse_error", [], fetched_at, {"error": str(exc)})

    result = payload.get("result", payload if isinstance(payload, dict) else {})
    items = result.get("annotations") or result.get("outages") or result.get("data") or []
    if not isinstance(items, list):
        return _result(False, "parse_error", [], fetched_at, {"shape": type(items).__name__})
    return _result(True, "ok", items, fetched_at, {"count": len(items)})


def _result(ok: bool, status: str, items: list[Dict[str, Any]], fetched_at: str, diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": SOURCE,
        "ok": ok,
        "status": status,
        "items": items,
        "diagnostics": diagnostics,
        "fetched_at": fetched_at,
    }
