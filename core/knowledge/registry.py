from __future__ import annotations

from typing import Dict, List, Optional

from core.knowledge.source import KnowledgeSource


class KnowledgeRegistry:
    def __init__(self) -> None:
        self._sources: Dict[str, KnowledgeSource] = {}

    def register_source(self, source: KnowledgeSource) -> KnowledgeSource:
        if not source.id:
            raise ValueError("Knowledge source id is required.")
        self._sources[source.id] = source
        return source

    def list_sources(self, agent_id: Optional[str] = None) -> List[KnowledgeSource]:
        if agent_id is None:
            return list(self._sources.values())
        normalized = agent_id.upper()
        return [
            source
            for source in self._sources.values()
            if normalized in [tag.upper() for tag in source.tags]
            or source.metadata.get("agent_id", "").upper() == normalized
        ]


DEFAULT_KNOWLEDGE_REGISTRY = KnowledgeRegistry()


def register_source(source: KnowledgeSource) -> KnowledgeSource:
    return DEFAULT_KNOWLEDGE_REGISTRY.register_source(source)


def list_sources(agent_id: Optional[str] = None) -> List[KnowledgeSource]:
    return DEFAULT_KNOWLEDGE_REGISTRY.list_sources(agent_id)

