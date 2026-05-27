from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SOURCE = "acled"
DEFAULT_BASE_URL = "https://acleddata.com/api/acled/read"
DEFAULT_TOKEN_URL = "https://acleddata.com/oauth/token"


def resolve_acled_auth(timeout: int = 8) -> Dict[str, Any]:
    access_token = os.getenv("ACLED_ACCESS_TOKEN", "").strip()
    if access_token:
        return {
            "ok": True,
            "auth_mode": "access_token",
            "headers": _auth_headers(access_token),
            "diagnostics": {"auth_mode": "access_token", "oauth_success": True},
        }

    email = os.getenv("ACLED_EMAIL", "").strip()
    password = os.getenv("ACLED_PASSWORD", "")
    if email and password:
        token_result = request_acled_oauth_token(email, password, timeout=timeout)
        if token_result.get("ok"):
            return {
                "ok": True,
                "auth_mode": "oauth_password",
                "headers": _auth_headers(str(token_result["access_token"])),
                "diagnostics": {
                    "auth_mode": "oauth_password",
                    "oauth_success": True,
                    "expires_in": token_result.get("expires_in"),
                },
            }
        return {
            "ok": False,
            "auth_mode": "oauth_password",
            "headers": {},
            "diagnostics": {
                "auth_mode": "oauth_password",
                "oauth_failed": True,
                "error": token_result.get("error", "OAuth token request failed."),
                "status": token_result.get("status"),
            },
        }

    legacy_enabled = os.getenv("ACLED_ENABLE_LEGACY_KEY", "").strip().lower() in {"1", "true", "yes", "on"}
    legacy_key = os.getenv("ACLED_API_KEY") or os.getenv("ACLED_KEY")
    if legacy_enabled and legacy_key and email:
        return {
            "ok": True,
            "auth_mode": "legacy_key",
            "headers": {"Accept": "application/json", "User-Agent": "CONSENSUS-BELLATOR/7.9"},
            "legacy_params": {"email": email, "key": legacy_key},
            "diagnostics": {"auth_mode": "legacy_key", "legacy_enabled": True},
        }

    return {
        "ok": False,
        "auth_mode": "missing_credentials",
        "headers": {},
        "diagnostics": {
            "missing_credentials": True,
            "requires": ["ACLED_ACCESS_TOKEN", "ACLED_EMAIL + ACLED_PASSWORD"],
            "legacy_fallback": "ACLED_ENABLE_LEGACY_KEY=1 with ACLED_EMAIL + ACLED_API_KEY/ACLED_KEY",
        },
    }


def request_acled_oauth_token(email: str, password: str, timeout: int = 8) -> Dict[str, Any]:
    token_url = os.getenv("ACLED_TOKEN_URL", DEFAULT_TOKEN_URL)
    body = urlencode(
        {
            "username": email,
            "password": password,
            "grant_type": "password",
            "client_id": "acled",
            "scope": "authenticated",
        }
    ).encode("utf-8")
    request = Request(
        token_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": exc.reason}
    except (URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "status": "network_error", "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status": "parse_error", "error": str(exc)}

    access_token = payload.get("access_token")
    if not access_token:
        return {"ok": False, "status": "missing_token", "error": "OAuth response did not include access_token."}
    _log_event("acled_oauth_token_acquired", {"message": "ACLED OAuth token acquired", "expires_in": payload.get("expires_in")})
    return {
        "ok": True,
        "access_token": access_token,
        "expires_in": payload.get("expires_in"),
        "refresh_token_present": bool(payload.get("refresh_token")),
    }


def fetch_acled_events(days: int = 3, limit: int = 100, timeout: int = 8) -> Dict[str, Any]:
    base_url = os.getenv("ACLED_BASE_URL", DEFAULT_BASE_URL)
    fetched_at = datetime.now(timezone.utc).isoformat()
    auth = resolve_acled_auth(timeout=timeout)

    if not auth.get("ok"):
        return _result(False, "missing_credentials", [], fetched_at, auth.get("diagnostics", {}))

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=max(days, 1))
    params = {
        "_format": "json",
        "limit": str(limit),
        "event_date": f"{start_date}|{end_date}",
        "event_date_where": "BETWEEN",
    }
    params.update(auth.get("legacy_params", {}))
    url = f"{base_url}?{urlencode(params)}"
    try:
        request = Request(url, headers=auth.get("headers", {}))
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        status = "token_expired" if exc.code in {401, 403} and auth.get("auth_mode") in {"access_token", "oauth_password"} else "http_error"
        diagnostics = dict(auth.get("diagnostics", {}))
        diagnostics.update({"code": exc.code, "reason": exc.reason})
        if status == "token_expired":
            diagnostics["token_expired"] = True
        return _result(False, status, [], fetched_at, diagnostics)
    except (URLError, TimeoutError, OSError) as exc:
        diagnostics = dict(auth.get("diagnostics", {}))
        diagnostics["error"] = str(exc)
        return _result(False, "network_error", [], fetched_at, diagnostics)
    except Exception as exc:
        diagnostics = dict(auth.get("diagnostics", {}))
        diagnostics["error"] = str(exc)
        return _result(False, "parse_error", [], fetched_at, diagnostics)

    items = payload.get("data", payload if isinstance(payload, list) else [])
    if not isinstance(items, list):
        diagnostics = dict(auth.get("diagnostics", {}))
        diagnostics["shape"] = type(items).__name__
        return _result(False, "parse_error", [], fetched_at, diagnostics)
    diagnostics = dict(auth.get("diagnostics", {}))
    diagnostics["count"] = len(items)
    return _result(True, "ok", items, fetched_at, diagnostics)


def _auth_headers(access_token: str) -> Dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "CONSENSUS-BELLATOR/7.9",
    }


def _log_event(event_type: str, payload: Dict[str, Any]) -> None:
    try:
        from core.logging import log_event
    except ImportError:
        try:
            from CONSENSUS_SYSTEM.core.logging import log_event
        except Exception:
            return
    try:
        log_event(event_type, payload)
    except Exception:
        return


def _result(ok: bool, status: str, items: list[Dict[str, Any]], fetched_at: str, diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": SOURCE,
        "ok": ok,
        "status": status,
        "items": items,
        "diagnostics": diagnostics,
        "fetched_at": fetched_at,
    }
