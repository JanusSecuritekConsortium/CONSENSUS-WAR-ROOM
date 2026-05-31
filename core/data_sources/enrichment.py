from __future__ import annotations

from typing import Any, Dict

from core.data_sources.registry import DataSourceRegistry, build_data_source_registry


ANTI_FABRICATION_RULE = "Do not invent external intelligence. Treat DATA_UNAVAILABLE sources as unavailable."


def build_bellator_data_enrichment(
    query: str = "",
    *,
    registry: DataSourceRegistry | None = None,
    live: bool = False,
) -> Dict[str, Any]:
    return _build("bellator", query, registry=registry, live=live)


def build_aeternum_data_enrichment(
    query: str = "",
    *,
    registry: DataSourceRegistry | None = None,
    live: bool = False,
) -> Dict[str, Any]:
    return _build("aeternum", query, registry=registry, live=live)


def _build(role: str, query: str, *, registry: DataSourceRegistry | None, live: bool) -> Dict[str, Any]:
    packet = (registry or build_data_source_registry()).collect(role, query, live=live)
    packet["label"] = f"{role.upper()} REAL DATA ENRICHMENT"
    packet["anti_fabrication_instruction"] = ANTI_FABRICATION_RULE
    if packet["status"] == "DATA_UNAVAILABLE":
        packet["degraded_reason"] = "No normalized source items available; external data is unavailable."
    return packet
