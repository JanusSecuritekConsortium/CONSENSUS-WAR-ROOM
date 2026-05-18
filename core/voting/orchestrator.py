from __future__ import annotations

import time
from typing import Any, Dict, Optional, Protocol

from config.names import TRIBUNAL_AGENT_IDS
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
            runtime_context["model"] = node.model
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
                    vote=VoteValue.ERROR,
                    confidence=0.0,
                    reasoning=f"Runtime failure: {exc}",
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
                    "model": vote.model,
                    "response_time": vote.response_time,
                },
                level="ERROR" if vote.vote == VoteValue.ERROR else "INFO",
            )
            if sequential:
                context[agent_id] = {
                    "vote": vote.vote.value,
                    "confidence": vote.confidence,
                    "reasoning": vote.reasoning,
                }

        return votes
