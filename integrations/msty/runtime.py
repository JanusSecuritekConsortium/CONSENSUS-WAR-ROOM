from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional

from config.agents import AgentProfile, get_agent_profile
from config.names import AETERNUM, AURELIUS, BELLATOR, RATIONALIS
from config.nodes import DEFAULT_NODES
from config.runtime import RuntimeConfig
from core.llm.backends import MockBackend
from core.logging import log_error, log_event


FallbackHook = Callable[[str, str, Optional[Dict[str, Any]], Exception], str]
TelemetryHook = Callable[[Dict[str, Any]], None]


@dataclass
class MstySession:
    session_id: str
    agent_id: str
    profile: AgentProfile
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used_at: str = field(default_factory=lambda: datetime.now().isoformat())
    turns: int = 0


class SessionRegistry:
    def __init__(self) -> None:
        self._sessions: Dict[str, MstySession] = {}

    def get_or_create(self, agent_id: str) -> MstySession:
        normalized = agent_id.upper()
        if normalized not in self._sessions:
            self._sessions[normalized] = MstySession(
                session_id=uuid.uuid4().hex,
                agent_id=normalized,
                profile=get_agent_profile(normalized),
            )
        session = self._sessions[normalized]
        session.last_used_at = datetime.now().isoformat()
        return session

    def list_sessions(self) -> Dict[str, MstySession]:
        return dict(self._sessions)

    def clear(self, agent_id: Optional[str] = None) -> None:
        if agent_id is None:
            self._sessions.clear()
            return
        self._sessions.pop(agent_id.upper(), None)


class MstyRuntime:
    """Session-owning orchestration adapter for Msty-backed agent execution."""

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        fallback_enabled: Optional[bool] = None,
        fallback_hooks: Optional[List[FallbackHook]] = None,
        telemetry_hooks: Optional[List[TelemetryHook]] = None,
    ) -> None:
        self.config = config or RuntimeConfig()
        self.session_registry = SessionRegistry()
        self.fallback_enabled = self.config.mock_fallback_enabled if fallback_enabled is None else fallback_enabled
        self.fallback_hooks = fallback_hooks or []
        self.telemetry_hooks = telemetry_hooks or []

    def send_to_agent(
        self,
        agent_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        session = self.session_registry.get_or_create(agent_id)
        session.turns += 1
        started = time.perf_counter()
        rendered_prompt = self._render_prompt(session, prompt, context)

        try:
            requested_model = str(
                (context or {}).get("model")
                or self.config.agent_model_overrides.get(session.agent_id)
                or session.profile.model_preference
            )
            if self.config.backend == "mock":
                response = self._mock_response(session.agent_id, prompt, context)
                provider = "mock"
            else:
                from integrations.msty import api as api_module

                health = self._provider_health(api_module)
                provider_state = str(health.get("status", "offline"))
                if provider_state == "offline":
                    raise RuntimeError(f"Provider offline at {health.get('base_url')}")
                resolved_models = health.get("resolved_required_models", {})
                if isinstance(resolved_models, dict) and session.agent_id in resolved_models:
                    requested_model = str(resolved_models[session.agent_id])
                else:
                    matched_model, _match_type = api_module.match_model_alias(requested_model, health.get("models", []))
                    if matched_model:
                        requested_model = matched_model
                if requested_model not in set(health.get("models", [])):
                    if health.get("model_remap_active") and health.get("model_remap_model"):
                        requested_model = str(health["model_remap_model"])
                    else:
                        raise RuntimeError(f"Required model unavailable for {session.agent_id}: {requested_model}")
                response = api_module.send_prompt(
                    requested_model,
                    rendered_prompt,
                    system_prompt=session.profile.system_prompt,
                    config=self.config,
                    base_url=health.get("base_url"),
                )
                provider = str(health.get("active_backend") or health.get("backend") or self.config.backend)
            self._record_telemetry(session, prompt, response, started, provider, "ready")
            return response
        except Exception as exc:
            log_error(
                "msty_runtime_send_error",
                exc,
                {
                    "agent_id": session.agent_id,
                    "session_id": session.session_id,
                    "backend": self.config.backend,
                },
            )
            if self.config.strict_provider_mode or not self.fallback_enabled:
                raise
            log_event(
                "provider_degraded_fallback",
                {
                    "agent_id": session.agent_id,
                    "session_id": session.session_id,
                    "backend": self.config.backend,
                    "fallback": "mock",
                    "error": str(exc),
                },
                level="WARNING",
            )
            response = self._fallback_response(session.agent_id, prompt, context, exc)
            self._record_telemetry(session, prompt, response, started, "mock-fallback", "degraded")
            return response

    def stream_to_agent(
        self,
        agent_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Iterator[str]:
        response = self.send_to_agent(agent_id, prompt, context)
        for chunk in self._chunk_response(response):
            yield chunk

    def health_check(self) -> Dict[str, Any]:
        from integrations.msty import api as api_module

        from config.nodes import DEFAULT_NODES

        status = self._provider_health(api_module, DEFAULT_NODES)
        runtime_status = "ready" if status.get("status") == "ready" else "degraded"
        payload = {
            "status": runtime_status,
            "provider": status,
            "fallback_enabled": self.fallback_enabled,
            "strict_provider_mode": self.config.strict_provider_mode,
            "fallback_policy": self.fallback_policy(status),
            "sessions": {
                agent_id: {
                    "session_id": session.session_id,
                    "turns": session.turns,
                    "last_used_at": session.last_used_at,
                }
                for agent_id, session in self.session_registry.list_sessions().items()
            },
        }
        log_event("msty_runtime_health", payload, level="INFO" if runtime_status == "ready" else "WARNING")
        return payload

    def fallback_policy(self, provider_status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        status = provider_status or self.health_check().get("provider", {})
        provider_state = str(status.get("status", "offline"))
        missing = status.get("missing_required_models", {})
        if self.config.strict_provider_mode:
            mode = "strict"
            action = "fail_if_provider_or_required_model_unavailable"
        elif status.get("model_remap_active"):
            mode = "degraded_model_remap"
            action = f"use_available_model:{status.get('model_remap_model')}"
        elif provider_state == "ready":
            mode = "real"
            action = "use_provider"
        elif provider_state == "degraded":
            mode = "degraded"
            action = "use_available_models_and_mock_missing" if self.fallback_enabled else "fail_missing_models"
        else:
            mode = "offline"
            action = "mock_all_monoliths" if self.fallback_enabled else "fail_provider_offline"
        return {
            "mode": mode,
            "action": action,
            "fallback_enabled": self.fallback_enabled,
            "strict_provider_mode": self.config.strict_provider_mode,
            "missing_required_models": missing,
        }

    def register_fallback_hook(self, hook: FallbackHook) -> None:
        self.fallback_hooks.append(hook)

    def register_telemetry_hook(self, hook: TelemetryHook) -> None:
        self.telemetry_hooks.append(hook)

    def _provider_health(self, api_module, nodes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            return api_module.health_check(self.config, nodes)
        except TypeError:
            return api_module.health_check(self.config)

    def _fallback_response(
        self,
        agent_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]],
        error: Exception,
    ) -> str:
        for hook in self.fallback_hooks:
            response = hook(agent_id, prompt, context, error)
            if response:
                return response
        return self._mock_response(agent_id, prompt, context)

    def _mock_response(self, agent_id: str, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        if agent_id in DEFAULT_NODES:
            return MockBackend().complete(DEFAULT_NODES[agent_id], prompt, context or {})
        if agent_id == AURELIUS:
            return (
                "AURELIUS STATUS: degraded mock runtime active.\n"
                "SUMMARY: Msty provider is unavailable or mock mode is selected.\n"
                "NEXT_ACTION: Continue local operation and submit proposals through ARBITER when ready."
            )
        return (
            "VOTE: ABSTAIN\n"
            "CONFIDENCE: 0.50\n"
            f"REASONING: Mock fallback for {agent_id} has no specialized runtime profile.\n"
            "RISKS: provider unavailable\n"
            "CONDITIONS: verify Msty provider health\n"
        )

    def _render_prompt(
        self,
        session: MstySession,
        prompt: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        context_block = f"\n\nContext:\n{context}" if context else ""
        return (
            f"Agent: {session.agent_id}\n"
            f"Session: {session.session_id}\n"
            f"Memory scope: {session.profile.memory_scope}\n"
            f"{context_block}\n\n"
            f"Prompt:\n{prompt}"
        )

    def _record_telemetry(
        self,
        session: MstySession,
        prompt: str,
        response: str,
        started: float,
        provider: str,
        status: str,
    ) -> None:
        elapsed = time.perf_counter() - started
        telemetry = {
            "agent_id": session.agent_id,
            "session_id": session.session_id,
            "provider": provider,
            "status": status,
            "latency_seconds": round(elapsed, 6),
            "prompt_tokens_estimate": self._estimate_tokens(prompt),
            "response_tokens_estimate": self._estimate_tokens(response),
            "turns": session.turns,
        }
        log_event("msty_runtime_telemetry", telemetry, level="INFO" if status == "ready" else "WARNING")
        for hook in self.telemetry_hooks:
            hook(telemetry)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text.split()))

    @staticmethod
    def _chunk_response(response: str, chunk_size: int = 240) -> Iterator[str]:
        for index in range(0, len(response), chunk_size):
            yield response[index : index + chunk_size]


__all__ = ["MstyRuntime", "MstySession", "SessionRegistry"]
