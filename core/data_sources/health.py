from __future__ import annotations

from typing import Any, Dict

from core.data_sources.normalization import utc_now_iso
from core.data_sources.registry import DataSourceRegistry, build_data_source_registry
from core.data_sources.source_config import load_data_source_config, missing_credentials, redacted_data_source_config


def build_data_sources_status(
    registry: DataSourceRegistry | None = None,
    *,
    attempt_live: bool = False,
) -> Dict[str, Any]:
    active = registry or build_data_source_registry()
    config = active.config
    health = active.health()
    enabled = [entry["source_id"] for entry in health if entry.get("enabled")]
    missing = {
        source_id: missing_credentials(source_id, source)
        for source_id, source in config.get("sources", {}).items()
        if missing_credentials(source_id, source)
    }
    bellator = active.collect("bellator", live=attempt_live)
    aeternum = active.collect("aeternum", live=attempt_live)
    return {
        "status": "READY" if any(entry.get("status") in {"READY", "CACHE_READY"} for entry in health) else "DEGRADED",
        "checked_at": utc_now_iso(),
        "mode": "live_refresh" if attempt_live else "cache_only",
        "enabled_sources": enabled,
        "source_health": health,
        "missing_credentials": missing,
        "redacted_config": redacted_data_source_config(config),
        "feeds": {"bellator": bellator, "aeternum": aeternum},
    }


def normalized_sample_items(status: Dict[str, Any], limit: int = 20) -> list[Dict[str, Any]]:
    samples: list[Dict[str, Any]] = []
    for feed in status.get("feeds", {}).values():
        for item in feed.get("items", []):
            if item.get("source") == "ibkr":
                item = {**item, "summary": "Read-only market snapshot", "raw_ref": None}
            samples.append(item)
            if len(samples) >= limit:
                return samples
    return samples
