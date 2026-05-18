from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from core.knowledge.registry import DEFAULT_KNOWLEDGE_REGISTRY


def retrieve_context(query: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
    """Return source metadata for future retrieval without vector search yet."""

    sources = DEFAULT_KNOWLEDGE_REGISTRY.list_sources(agent_id)
    query_terms = {term.lower() for term in query.split() if term.strip()}
    matched = []
    for source in sources:
        haystack = " ".join([source.title, source.location, " ".join(source.tags)]).lower()
        if not query_terms or any(term in haystack for term in query_terms):
            matched.append(asdict(source))
    return {
        "query": query,
        "agent_id": agent_id,
        "sources": matched,
        "retrieval_mode": "metadata_only",
    }

