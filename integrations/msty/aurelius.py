from __future__ import annotations

from typing import Any, Dict, Optional

from config.names import AURELIUS
from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from core.history import result_to_dict
from core.memory.store import MemoryStore
from core.tribunal import Tribunal
from core.voting.rules import ConsensusRules
from integrations.msty.runtime import MstyRuntime


class AureliusOperator:
    """Executive/operator layer for Msty Claw style workflows. It does not vote."""

    def __init__(
        self,
        runtime: Optional[MstyRuntime] = None,
        memory: Optional[MemoryStore] = None,
    ) -> None:
        self.runtime = runtime or MstyRuntime(RuntimeConfig())
        self.memory = memory or MemoryStore()

    def summarize_system_state(self) -> Dict[str, Any]:
        runtime_health = self.runtime.health_check()
        memory = self.memory.load()
        return {
            "runtime": runtime_health,
            "memory_decisions": len(memory.get("decisions", [])),
            "known_agents": sorted(memory.get("agents", {}).keys()),
        }

    def submit_proposal_to_arbiter(
        self,
        proposal: str,
        theme_key: str = "military",
        advisory: bool = False,
    ) -> Dict[str, Any]:
        if advisory:
            self.runtime.send_to_agent(
                AURELIUS,
                "Prepare an advisory operator note. Do not cast a tribunal vote.",
                {"proposal": proposal},
            )
        tribunal = Tribunal(
            DEFAULT_NODES,
            self.runtime,
            rules=ConsensusRules(),
            theme_key=theme_key,
        )
        return result_to_dict(tribunal.deliberate(proposal))

    def query_memory(self, query: str) -> Dict[str, Any]:
        memory = self.memory.load()
        decisions = memory.get("decisions", [])
        terms = {term.lower() for term in query.split() if term.strip()}
        matches = [
            decision
            for decision in decisions
            if not terms
            or any(term in str(decision).lower() for term in terms)
        ]
        return {"query": query, "matches": matches[-20:]}

    def call_workflow_integration(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "integration": name,
            "status": "not_configured",
            "payload": payload,
        }

    def prepare_user_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        return self.runtime.send_to_agent(AURELIUS, prompt, context)

