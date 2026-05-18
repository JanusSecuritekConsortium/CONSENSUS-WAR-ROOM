from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from core.history import record_result
from core.logging import log_event
from core.memory.context import build_context_packet
from core.memory.session import upsert_session_record
from core.models import NodeIdentity, TribunalResult
from core.themes import THEMES
from core.voting.engine import ConsensusEngine
from core.voting.orchestrator import AgentRuntime, VotingOrchestrator
from core.voting.rules import ConsensusRules


class Tribunal:
    def __init__(
        self,
        nodes: Dict[str, NodeIdentity],
        runtime: AgentRuntime,
        rules: Optional[ConsensusRules] = None,
        theme_key: str = "military",
    ):
        self.nodes = nodes
        self.runtime = runtime
        self.rules = rules or ConsensusRules()
        self.theme_key = theme_key if theme_key in THEMES else "military"
        self.orchestrator = VotingOrchestrator(nodes, runtime)
        self.consensus_engine = ConsensusEngine(self.rules, self.theme_key)

    def deliberate(self, query: str, sequential: bool = False) -> TribunalResult:
        session_id = uuid.uuid4().hex[:12]
        memory_context = build_context_packet(query)
        provider_context = self._provider_context()
        log_event(
            "proposal",
            {
                "session_id": session_id,
                "theme": self.theme_key,
                "sequential": sequential,
                "query": query,
                "prior_decisions_used": memory_context.get("prior_decisions_used", 0),
            },
        )
        started = time.perf_counter()
        votes = self.orchestrator.cast_votes(query, session_id, self.theme_key, sequential, memory_context)
        result = self.consensus_engine.calculate_result(query, votes, session_id)
        record_result(result)
        self._record_session_memory(result, memory_context, provider_context)
        log_event(
            "verdict",
            {
                "session_id": session_id,
                "verdict": result.verdict.value,
                "confidence": result.confidence,
                "review_triggers": result.review_triggers,
                "elapsed": round(time.perf_counter() - started, 6),
            },
        )
        return result

    def _provider_context(self) -> Dict[str, Any]:
        if not hasattr(self.runtime, "health_check"):
            return {"status": "unknown"}
        try:
            payload = self.runtime.health_check()  # type: ignore[attr-defined]
            provider = payload.get("provider", payload) if isinstance(payload, dict) else {}
            return provider if isinstance(provider, dict) else {}
        except Exception as exc:
            return {"status": "unknown", "error": str(exc)}

    def _record_session_memory(
        self,
        result: TribunalResult,
        memory_context: Dict[str, Any],
        provider_context: Dict[str, Any],
    ) -> None:
        model_mapping = {
            agent_id: vote.model
            for agent_id, vote in result.votes.items()
        }
        record = {
            "session_id": result.session_id,
            "active_theme": result.theme,
            "proposal": result.query,
            "monolith_votes": {
                agent_id: {
                    "vote": vote.vote.value,
                    "confidence": vote.confidence,
                    "reasoning": vote.reasoning,
                    "model": vote.model,
                    "response_time": vote.response_time,
                }
                for agent_id, vote in result.votes.items()
            },
            "arbiter_verdict": result.verdict.value,
            "verdict": result.verdict.value,
            "synthesis_summary": result.reason,
            "provider_backend": provider_context.get("active_backend") or provider_context.get("backend"),
            "provider_status": provider_context.get("status"),
            "model_mapping": model_mapping,
            "timestamp": result.timestamp,
            "tags": [],
            "context": {
                "retrieval": memory_context.get("retrieval"),
                "prior_decisions_used": memory_context.get("prior_decisions_used", 0),
                "items": memory_context.get("items", []),
            },
        }
        try:
            upsert_session_record(record)
        except Exception as exc:
            log_event("session_memory_write_failed", {"session_id": result.session_id, "error": str(exc)}, level="WARN")
