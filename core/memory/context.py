from __future__ import annotations

from typing import Any, Dict, List

from core.memory.retrieval import retrieve_relevant_context
from core.knowledge.second_brain import shared_brain_context
from core.knowledge.ghostnotes import search as search_ghostnotes


def build_context_packet(query: str, tags: List[str] | None = None, limit: int = 3) -> Dict[str, Any]:
    packet = retrieve_relevant_context(query, tags=tags, limit=limit)
    packet["second_brain"] = shared_brain_context()
    if isinstance(query, str) and query.strip():
        references = search_ghostnotes(query[:2000], limit=3)
        if references["matches"]:
            packet["external_reference_context"] = references
    return packet


def context_status(packet: Dict[str, Any] | None) -> str:
    if packet and int(packet.get("prior_decisions_used", 0) or 0) > 0:
        return "ACTIVE"
    return "NONE"
