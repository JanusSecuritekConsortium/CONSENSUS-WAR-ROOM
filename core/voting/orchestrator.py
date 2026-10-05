from __future__ import annotations

from copy import deepcopy
import time
from typing import Any, Callable, Dict, Optional, Protocol

from config.version import SYSTEM_VERSION
from config.names import AETERNUM, BELLATOR, TRIBUNAL_AGENT_IDS
from core.data_sources.enrichment import build_aeternum_data_enrichment
from core.intelligence.bellator_context_builder import ANTI_FABRICATION_INSTRUCTION, build_bellator_context_packet
from core.llm.prompts import build_node_prompt
from core.logging import log_error, log_event
from core.models import NodeIdentity, Vote, VoteValue
from core.voting.parser import parse_vote


DELIBERATION_PHASES = ("assessment", "critique", "revision")


class AgentRuntime(Protocol):
    def send_to_agent(self, agent_id: str, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        ...


class VotingOrchestrator:
    """Three round barriers: no agent sees an unfinished round's responses."""

    def __init__(self, nodes: Dict[str, NodeIdentity], runtime: AgentRuntime) -> None:
        self.nodes = nodes
        self.runtime = runtime
        self.transcript: list[Dict[str, Any]] = []
        self.complete = False
        self.simulation = getattr(getattr(runtime, "config", None), "backend", None) == "mock"

    def cast_votes(
        self, query: str, session_id: str, theme_key: str, sequential: bool = False,
        memory_context: Optional[Dict[str, Any]] = None,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Vote]:
        # Kept for API compatibility. All submissions now use the same round barriers.
        self.transcript = []
        self.complete = False
        base_context = {
            "session_id": session_id, "theme": theme_key,
            "memory_context": memory_context or {"prior_decisions_used": 0, "items": [], "summary": "No prior decisions retrieved."},
            "require_real_model": not self.simulation,
        }
        packets = {
            BELLATOR: {"bellator_context_packet": self._build_bellator_context_packet(query)},
            AETERNUM: {"aeternum_data_packet": build_aeternum_data_enrichment(query, live=False)},
        }
        votes: Dict[str, Vote] = {}
        previous_rounds: list[Dict[str, Any]] = []

        for number, phase in enumerate(DELIBERATION_PHASES, 1):
            self._emit(on_event, {"type": "round_started", "round": number, "phase": phase})
            round_votes: Dict[str, Vote] = {}
            for agent_id in TRIBUNAL_AGENT_IDS:
                node = self.nodes[agent_id]
                runtime_context = deepcopy(base_context)
                runtime_context.update(deepcopy(packets.get(agent_id, {})))
                runtime_context.update({
                    "model": node.model, "temperature": node.temperature, "max_output_tokens": node.max_output_tokens,
                    "deliberation": {"round": number, "phase": phase, "total_rounds": len(DELIBERATION_PHASES), "previous_rounds": deepcopy(previous_rounds)},
                })
                self._emit(on_event, {"type": "agent_started", "round": number, "phase": phase, "agent_id": agent_id, "context": deepcopy(runtime_context)})
                started = time.perf_counter()
                raw = ""
                prompt = build_node_prompt(node, query, runtime_context)
                try:
                    raw = self.runtime.send_to_agent(agent_id, prompt, runtime_context)
                    execution = getattr(self.runtime, "last_execution", {}).get(agent_id, {})
                    backend = str(execution.get("backend") or ("mock" if self.simulation else "msty-runtime"))
                    vote = parse_vote(raw, node, time.perf_counter() - started, backend)
                    vote.node_key = agent_id
                    vote.backend = backend
                    vote.model = str(execution.get("model") or vote.model)
                    if not self.simulation and backend in {"mock", "mock-fallback"}:
                        raise RuntimeError("Simulated response cannot count as real-model deliberation")
                except Exception as exc:
                    execution = getattr(self.runtime, "last_execution", {}).get(agent_id, {})
                    log_error("vote_error", exc, {"session_id": session_id, "agent_id": agent_id, "model": node.model, "round": number, "phase": phase})
                    vote = Vote(
                        node_key=agent_id, role=node.role, vote=VoteValue.ABSTAIN, confidence=0.0,
                        reasoning=f"Model call failed during {phase}: {exc}",
                        validation_errors=[f"runtime_failure:{type(exc).__name__}"], model=str(execution.get("model") or node.model),
                        response_time=time.perf_counter() - started, raw_response=raw, backend=str(execution.get("backend") or "failed"),
                    )
                round_votes[agent_id] = vote
                entry = {
                    "round": number, "phase": phase, "agent_id": agent_id,
                    "status": "failed" if vote.validation_errors else ("simulation" if self.simulation else "completed"),
                    "model": vote.model, "requested_model": node.model, "backend": vote.backend,
                    "temperature": node.temperature, "max_output_tokens": node.max_output_tokens,
                    "vote": vote.vote.value, "confidence": vote.confidence, "evidence_quality": vote.evidence_quality,
                    "critical_risk": vote.critical_risk, "reasoning": vote.reasoning,
                    "risks": list(vote.risks), "conditions": list(vote.conditions),
                    "validation_errors": list(vote.validation_errors), "raw_response": vote.raw_response,
                    "response_time": vote.response_time,
                }
                self.transcript.append(entry)
                log_event("deliberation_turn", {"session_id": session_id, **entry}, level="ERROR" if vote.validation_errors else "INFO")
                if phase == "revision":
                    log_event("vote", {"session_id": session_id, **entry}, level="ERROR" if vote.validation_errors else "INFO")
                self._emit(on_event, {"type": "vote_received", "round": number, "phase": phase, "agent_id": agent_id, "vote": vote})
            votes = round_votes
            self._emit(on_event, {"type": "round_completed", "round": number, "phase": phase})
            if any(vote.validation_errors for vote in votes.values()):
                log_event("deliberation_incomplete", {"session_id": session_id, "round": number, "phase": phase}, level="ERROR")
                break
            previous_rounds.append({"round": number, "phase": phase, "assessments": {key: self._discussion_view(vote) for key, vote in votes.items()}})
        else:
            self.complete = True
        return votes

    @staticmethod
    def _discussion_view(vote: Vote) -> Dict[str, Any]:
        # Bound prompt growth; the local audit transcript retains the full response.
        return {
            "vote": vote.vote.value, "confidence": vote.confidence, "evidence_quality": vote.evidence_quality,
            "critical_risk": vote.critical_risk, "reasoning": vote.reasoning[:900],
            "risks": [risk[:120] for risk in vote.risks[:2]],
            "conditions": [condition[:120] for condition in vote.conditions[:2]],
            "excerpted": len(vote.reasoning) > 900 or len(vote.risks) > 2 or len(vote.conditions) > 2 or any(len(item) > 120 for item in [*vote.risks, *vote.conditions]),
        }

    @staticmethod
    def _emit(callback: Optional[Callable[[Dict[str, Any]], None]], event: Dict[str, Any]) -> None:
        if callback:
            callback(event)

    def attach_audit(self, result: Any) -> None:
        result.deliberation_transcript = deepcopy(self.transcript)
        result.deliberation_complete = self.complete
        result.simulation = self.simulation
        if self.simulation:
            result.review_triggers.append("simulation_only")
            result.reason = "SIMULATION ONLY: " + result.reason

    def _build_bellator_context_packet(self, query: str) -> Dict[str, Any]:
        try:
            return build_bellator_context_packet(query)
        except Exception as exc:
            log_error("bellator_context_packet_error", exc, {"query": query[:160]})
            return {
                "label": "BELLATOR CONTEXT PACKET", "version": SYSTEM_VERSION, "mode": "error", "events": [],
                "risk": {"risk_level": "UNKNOWN", "risk_score": 0.0}, "sources": {},
                "anti_fabrication_instruction": ANTI_FABRICATION_INSTRUCTION,
                "operator_note": f"Bellator feed context unavailable: {exc}",
            }
