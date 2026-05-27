from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SOURCE = "abuse_ch_urlhaus"
DEFAULT_RECENT_URL = "https://urlhaus-api.abuse.ch/v1/urls/recent/"


def fetch_urlhaus_recent(timeout: int = 8) -> Dict[str, Any]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    auth_key = os.getenv("URLHAUS_AUTH_KEY")
    enabled = os.getenv("URLHAUS_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return _result(False, "disabled", [], fetched_at, {"enable_with": "URLHAUS_ENABLED=1"})

    url = os.getenv("URLHAUS_RECENT_URL", DEFAULT_RECENT_URL)
    headers = {"Accept": "application/json", "User-Agent": "CONSENSUS-BELLATOR/7.9"}
    if auth_key:
        headers["Auth-Key"] = auth_key
    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return _result(False, "http_error", [], fetched_at, {"code": exc.code, "reason": exc.reason})
    except (URLError, TimeoutError, OSError) as exc:
        return _result(False, "network_error", [], fetched_at, {"error": str(exc)})
    except Exception as exc:
        return _result(False, "parse_error", [], fetched_at, {"error": str(exc)})

    items = _extract_items(payload)
    return _result(True, "ok", items, fetched_at, {"count": len(items)})


def _extract_items(payload: Any) -> list[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("urls"), list):
            return [item for item in payload["urls"] if isinstance(item, dict)]
        return [item for item in payload.values() if isinstance(item, dict)]
    return []


def _result(ok: bool, status: str, items: list[Dict[str, Any]], fetched_at: str, diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": SOURCE,
        "ok": ok,
        "status": status,
        "items": items,
        "diagnostics": diagnostics,
        "fetched_at": fetched_at,
    }
