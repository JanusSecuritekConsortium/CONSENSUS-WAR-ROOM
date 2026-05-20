from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

try:
    from core.intelligence.bellator_context_builder import FEED_CACHE_DIR
    from config.version import SYSTEM_VERSION
except ImportError:
    from .bellator_context_builder import FEED_CACHE_DIR
    from ...config.version import SYSTEM_VERSION

try:
    from integrations.feeds.abuse_ch_client import fetch_urlhaus_recent
    from integrations.feeds.acled_client import fetch_acled_events
    from integrations.feeds.cloudflare_radar_client import fetch_cloudflare_outages
    from integrations.feeds.nasa_firms_client import fetch_nasa_firms_events
except ImportError:
    from CONSENSUS_SYSTEM.integrations.feeds.abuse_ch_client import fetch_urlhaus_recent
    from CONSENSUS_SYSTEM.integrations.feeds.acled_client import fetch_acled_events
    from CONSENSUS_SYSTEM.integrations.feeds.cloudflare_radar_client import fetch_cloudflare_outages
    from CONSENSUS_SYSTEM.integrations.feeds.nasa_firms_client import fetch_nasa_firms_events


FetchFunc = Callable[[], Dict[str, Any]]


@dataclass(frozen=True)
class FeedHealthSpec:
    source: str
    required_environment: List[str]
    credential_groups: List[List[str]]
    fetcher: FetchFunc
    optional_environment: List[str] | None = None
    opt_in_variable: str | None = None


FEED_HEALTH_SPECS: List[FeedHealthSpec] = [
    FeedHealthSpec(
        source="acled",
        required_environment=["ACLED_ACCESS_TOKEN", "ACLED_EMAIL + ACLED_PASSWORD"],
        credential_groups=[["ACLED_ACCESS_TOKEN", "ACLED_OAUTH_PAIR"]],
        optional_environment=["ACLED_ENABLE_LEGACY_KEY", "ACLED_API_KEY", "ACLED_KEY"],
        fetcher=lambda: fetch_acled_events(days=1, limit=5, timeout=6),
    ),
    FeedHealthSpec(
        source="nasa_firms",
        required_environment=["NASA_FIRMS_MAP_KEY or FIRMS_MAP_KEY"],
        credential_groups=[["NASA_FIRMS_MAP_KEY", "FIRMS_MAP_KEY"]],
        fetcher=lambda: fetch_nasa_firms_events(days=1, timeout=6),
    ),
    FeedHealthSpec(
        source="cloudflare_radar",
        required_environment=["CLOUDFLARE_API_TOKEN or CLOUDFLARE_RADAR_TOKEN"],
        credential_groups=[["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_RADAR_TOKEN"]],
        fetcher=lambda: fetch_cloudflare_outages(days=1, limit=5, timeout=6),
    ),
    FeedHealthSpec(
        source="abuse_ch_urlhaus",
        required_environment=["URLHAUS_ENABLED=1"],
        credential_groups=[["URLHAUS_ENABLED"]],
        optional_environment=["URLHAUS_AUTH_KEY"],
        opt_in_variable="URLHAUS_ENABLED",
        fetcher=lambda: fetch_urlhaus_recent(timeout=6),
    ),
]


ENV_TEMPLATE_LINES = [
    '$env:ACLED_ACCESS_TOKEN=""',
    '$env:ACLED_EMAIL=""',
    '$env:ACLED_PASSWORD=""',
    '$env:NASA_FIRMS_MAP_KEY=""',
    '$env:CLOUDFLARE_API_TOKEN=""',
    '$env:URLHAUS_ENABLED="0"',
    '$env:URLHAUS_AUTH_KEY=""',
]


def build_feed_health_report(*, attempt_live: bool = True) -> Dict[str, Any]:
    FEED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    sources = [check_feed_health(spec, attempt_live=attempt_live) for spec in FEED_HEALTH_SPECS]
    return {
        "label": "BELLATOR FEED HEALTH",
        "version": SYSTEM_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cache_dir": str(FEED_CACHE_DIR),
        "sources": sources,
    }


def check_feed_health(spec: FeedHealthSpec, *, attempt_live: bool = True) -> Dict[str, Any]:
    cache_path = _cache_path(spec.source)
    cache_age = _cache_age_seconds(cache_path)
    credentials_present = _credentials_present(spec)
    live_check_attempted = bool(attempt_live and credentials_present)
    result_status = "not_attempted"
    http_status: Any = None
    usable = False
    diagnostic = _credential_message(spec, credentials_present)

    if live_check_attempted:
        result = _safe_fetch(spec)
        result_status = str(result.get("status", "unknown"))
        diagnostics = result.get("diagnostics", {}) if isinstance(result.get("diagnostics"), dict) else {}
        http_status = diagnostics.get("code")
        usable = bool(result.get("ok")) and result_status == "ok"
        diagnostic = _live_result_message(spec.source, result_status, usable, diagnostics)
        _write_json(cache_path, result)

    return {
        "source": spec.source,
        "required_environment": spec.required_environment,
        "optional_environment": spec.optional_environment or [],
        "credentials_present": credentials_present,
        "live_check_attempted": live_check_attempted,
        "http_status": http_status,
        "result_status": result_status,
        "cache_file_path": str(cache_path),
        "cache_age_seconds": cache_age,
        "usable": usable,
        "diagnostic": diagnostic,
    }


def print_env_template() -> str:
    return "\n".join(ENV_TEMPLATE_LINES)


def _safe_fetch(spec: FeedHealthSpec) -> Dict[str, Any]:
    try:
        result = spec.fetcher()
    except Exception as exc:
        return {
            "source": spec.source,
            "ok": False,
            "status": "client_error",
            "items": [],
            "diagnostics": {"error": str(exc)},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    if not isinstance(result, dict):
        return {
            "source": spec.source,
            "ok": False,
            "status": "client_error",
            "items": [],
            "diagnostics": {"error": f"unexpected result type: {type(result).__name__}"},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    return result


def _credentials_present(spec: FeedHealthSpec) -> bool:
    if spec.opt_in_variable:
        return os.getenv(spec.opt_in_variable, "").strip().lower() in {"1", "true", "yes", "on"}
    return all(any(_env_has_value(name) for name in group) for group in spec.credential_groups)


def _credential_message(spec: FeedHealthSpec, credentials_present: bool) -> str:
    if credentials_present:
        return "Credentials present; live check not attempted by request."
    if spec.opt_in_variable:
        return f"{spec.source} live check disabled; set {spec.opt_in_variable}=1 to opt in."
    return f"Missing required environment: {', '.join(spec.required_environment)}."


def _live_result_message(source: str, status: str, usable: bool, diagnostics: Dict[str, Any]) -> str:
    if usable:
        return f"{source} live check succeeded."
    if diagnostics:
        return f"{source} live check returned {status}: {json.dumps(diagnostics, ensure_ascii=True)}"
    return f"{source} live check returned {status}."


def _env_has_value(name: str) -> bool:
    if name == "ACLED_OAUTH_PAIR":
        return bool(os.getenv("ACLED_EMAIL", "").strip() and os.getenv("ACLED_PASSWORD", ""))
    return bool(os.getenv(name, "").strip())


def _cache_path(source: str) -> Path:
    return FEED_CACHE_DIR / f"{source}.json"


def _cache_age_seconds(path: Path) -> int | None:
    try:
        if not path.exists():
            return None
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except OSError:
        return None
    return max(0, int((datetime.now(timezone.utc) - modified).total_seconds()))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate BELLATOR feed API key setup")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="print feed health diagnostics")
    group.add_argument("--print-env-template", action="store_true", help="print PowerShell environment template")
    parser.add_argument("--no-live", action="store_true", help="skip live checks even when credentials are present")
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    if args.print_env_template:
        print(print_env_template())
        return 0
    if args.check:
        print(json.dumps(build_feed_health_report(attempt_live=not args.no_live), indent=2, ensure_ascii=True))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
