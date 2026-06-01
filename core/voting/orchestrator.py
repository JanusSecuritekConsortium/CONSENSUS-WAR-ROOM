from __future__ import annotations

import time
from typing import Any, Dict, Optional, Protocol

from config.version import SYSTEM_VERSION
from config.names import AETERNUM, BELLATOR, TRIBUNAL_AGENT_IDS
from core.data_sources.enrichment import build_aeternum_data_enrichment
from core.intelligence.bellator_context_builder import ANTI_FABRICATION_INSTRUCTION, build_bellator_context_packet
from core.llm.prompts import build_node_prompt
from core.logging import log_error, log_event
from core.models import NodeIdentity, Vote, VoteValue
from core.voting.parser import parse_vote


class AgentRuntime(Protocol):
    def send_to_agent(
        self,
        agent_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        ...


class VotingOrchestrator:
    def __init__(self, nodes: Dict[str, NodeIdentity], runtime: AgentRuntime) -> None:
        self.nodes = nodes
        self.runtime = runtime

    def cast_votes(
        self,
        query: str,
        session_id: str,
        theme_key: str,
        sequential: bool = False,
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Vote]:
        context: Dict[str, Any] = {
            "session_id": session_id,
            "theme": theme_key,
            "memory_context": memory_context or {"prior_decisions_used": 0, "items": [], "summary": "No prior decisions retrieved."},
        }
        votes: Dict[str, Vote] = {}

        for agent_id in TRIBUNAL_AGENT_IDS:
            node = self.nodes[agent_id]
            runtime_context = context if sequential else {
                "session_id": session_id,
                "theme": theme_key,
                "memory_context": context["memory_context"],
            }
            if agent_id == BELLATOR:
                runtime_context = dict(runtime_context)
            runtime_context["model"] = node.model
            if agent_id == BELLATOR:
                runtime_context["bellator_context_packet"] = self._build_bellator_context_packet(query)
            if agent_id == AETERNUM:
                runtime_context["aeternum_data_packet"] = build_aeternum_data_enrichment(query, live=False)
            prompt = build_node_prompt(node, query, runtime_context)
            started = time.perf_counter()
            try:
                raw = self.runtime.send_to_agent(agent_id, prompt, runtime_context)
                elapsed = time.perf_counter() - started
                vote = parse_vote(raw, node, elapsed, "msty-runtime")
                vote.node_key = agent_id
            except Exception as exc:
                elapsed = time.perf_counter() - started
                log_error(
                    "vote_error",
                    exc,
                    {
                        "session_id": session_id,
                        "agent_id": agent_id,
                        "model": node.model,
                        "elapsed": elapsed,
                    },
                )
                vote = Vote(
                    node_key=agent_id,
                    role=node.role,
                    vote=VoteValue.ABSTAIN,
                    confidence=0.0,
                    reasoning=f"Runtime failure: {exc}",
                    evidence_quality=0.0,
                    critical_risk=False,
                    validation_errors=[f"runtime_failure:{exc.__class__.__name__}"],
                    model=node.model,
                    response_time=elapsed,
                )

            votes[agent_id] = vote
            log_event(
                "vote",
                {
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "vote": vote.vote.value,
                    "confidence": vote.confidence,
                    "evidence_quality": vote.evidence_quality,
                    "critical_risk": vote.critical_risk,
                    "validation_errors": vote.validation_errors,
                    "model": vote.model,
                    "response_time": vote.response_time,
                },
                level="ERROR" if vote.validation_errors else "INFO",
            )
            if sequential:
                context[agent_id] = {
                    "vote": vote.vote.value,
                    "confidence": vote.confidence,
                    "reasoning": vote.reasoning,
                }

        return votes

    def _build_bellator_context_packet(self, query: str) -> Dict[str, Any]:
        try:
            return build_bellator_context_packet(query)
        except Exception as exc:
            log_error("bellator_context_packet_error", exc, {"query": query[:160]})
            return {
                "label": "BELLATOR CONTEXT PACKET",
                "version": SYSTEM_VERSION,
                "mode": "error",
                "events": [],
                "risk": {"risk_level": "UNKNOWN", "risk_score": 0.0},
                "sources": {},
                "anti_fabrication_instruction": ANTI_FABRICATION_INSTRUCTION,
                "operator_note": f"Bellator feed context unavailable: {exc}",
            }
