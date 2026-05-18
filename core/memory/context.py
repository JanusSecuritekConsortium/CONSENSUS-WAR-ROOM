from __future__ import annotations

from typing import Any, Dict, List

from core.memory.retrieval import retrieve_relevant_context


def build_context_packet(query: str, tags: List[str] | None = None, limit: int = 3) -> Dict[str, Any]:
    return retrieve_relevant_context(query, tags=tags, limit=limit)


def context_status(packet: Dict[str, Any] | None) -> str:
    if packet and int(packet.get("prior_decisions_used", 0) or 0) > 0:
        return "ACTIVE"
    return "NONE"
