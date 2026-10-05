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
        agent_runtime: Any = None,
    ) -> None:
        self.runtime = runtime or MstyRuntime(RuntimeConfig())
        self.memory = memory or MemoryStore()
        self.agent_runtime = agent_runtime
        self._agent_tasks = None
        self._odysseus_runtime = None

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
        if name == 'personal_action':
            from .personal.action_tools import handle
            return handle(payload)
        if name == 'briefing_memory':
            from .personal.publication import recall
            return recall(payload.get('mode', 'latest'))
        if name == 'personal_sources':
            from .personal.service import source_status
            return source_status()
        if name == 'personal_review':
            from .personal.service import personal_review
            return personal_review(payload.get('mode', 'morning'))
        return {
            "integration": name,
            "status": "not_configured",
            "payload": payload,
        }

    def prepare_user_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        from integrations.odysseus.client import OdysseusConfig
        try:
            if OdysseusConfig.from_env().enabled:
                return self.run_odysseus(prompt, context).text
        except ValueError:
            return 'AURELIUS Odysseus configuration is invalid; no agent action was executed.'
        from assistant.agent.config import AgentConfig
        try:
            config = AgentConfig.from_env()
        except ValueError:
            from assistant.agent.loop import audit
            audit('configuration_degraded')
            return 'AURELIUS agent configuration is invalid; no agent action was executed.'
        if config.enabled or (self.agent_runtime is not None and self.agent_runtime.config.enabled):
            return self.run_agent(prompt, context).text
        return self.runtime.send_to_agent(AURELIUS, prompt, context)

    def run_odysseus(self, prompt: str, context: Optional[Dict[str, Any]] = None):
        """Real external Odysseus engine, independently of the local agent option."""
        if self._odysseus_runtime is None:
            from integrations.odysseus.service import OdysseusRuntime
            self._odysseus_runtime = OdysseusRuntime()
        return self._odysseus_runtime.run(prompt, evidence=context)

    def run_agent(self, prompt: str, context: Optional[Dict[str, Any]] = None):
        """Explicit execution API; callers can display status and exact pending actions."""
        if self.agent_runtime is None:
            try:
                from assistant.agent.config import AgentConfig
                from assistant.agent.contracts import AgentResult
                settings = AgentConfig.from_env()
                if not settings.enabled:
                    return AgentResult('', 'disabled', '', reason='feature_disabled')
                from assistant.agent.service import build_agent
                self.agent_runtime = build_agent(operator=self, config=settings)
            except Exception as error:
                from assistant.agent.contracts import AgentResult
                from assistant.agent.loop import audit
                audit('setup_degraded', error_type=type(error).__name__)
                return AgentResult('', 'degraded', 'AURELIUS agent setup is unavailable; no action was executed.',
                                   reason='setup_failure')
        return self.agent_runtime.run(prompt, evidence=context)

    def resume_agent(self, run_id: str):
        if self.agent_runtime is None:
            raise ValueError('No agent runtime is attached')
        return self.agent_runtime.resume(run_id)

    def agent_tasks(self, path=None):
        """Explicit host-owned background integration; never starts at import/UI boot."""
        if self._agent_tasks is None:
            from assistant.agent.config import AgentConfig
            settings = self.agent_runtime.config if self.agent_runtime is not None else AgentConfig.from_env()
            if not settings.enabled or not settings.background_enabled:
                raise ValueError('AURELIUS agent/background flags must both be enabled')
            if self.agent_runtime is None:
                from assistant.agent.service import build_agent
                self.agent_runtime = build_agent(operator=self, config=settings)
            from assistant.agent.jobs import BackgroundTasks
            from core.paths import ARBITER_DIR
            self._agent_tasks = BackgroundTasks(self.agent_runtime, path or ARBITER_DIR / 'aurelius_agent' / 'jobs.sqlite')
        return self._agent_tasks
