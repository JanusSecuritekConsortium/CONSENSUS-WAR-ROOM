from __future__ import annotations

import os
from typing import Any, Dict, List

from config.runtime import RuntimeConfig
from core.llm.prompts import build_node_prompt
from core.models import LLMBackend, NodeIdentity, VoteValue

try:
    import requests
except ImportError:  # pragma: no cover - optional runtime dependency
    requests = None


class ProviderRequestError(RuntimeError):
    """Normalized provider connectivity failure without leaking raw requests errors."""


def _request_exceptions() -> tuple[type[BaseException], ...]:
    if requests is None:
        return ()
    return (requests.ConnectionError, requests.Timeout, requests.RequestException)


class MockBackend:
    """Deterministic-ish local backend for demos and offline testing."""

    name = "mock"

    def complete(self, node: NodeIdentity, query: str, context: Dict[str, Any]) -> str:
        lowered = self._proposal_text(query).lower()
        deny_terms = ["unsafe", "illegal", "breach", "exploit", "delete", "panic"]
        approve_terms = ["document", "analyze", "review", "prototype", "test", "improve"]
        conditional_terms = ["deploy", "production", "spend", "investment", "security"]
        critical_terms = ["deadlock", "override", "legal", "medical", "financial advice", "irreversible"]

        score = 0
        score += sum(1 for term in approve_terms if term in lowered)
        score -= sum(1 for term in deny_terms if term in lowered) * 2
        score -= 1 if node.role == "Security" and any(term in lowered for term in conditional_terms) else 0
        score -= 1 if node.role == "Finance" and any(term in lowered for term in ["spend", "buy", "investment"]) else 0

        critical_risk = any(term in lowered for term in critical_terms)
        if critical_risk:
            vote = VoteValue.DENY
            confidence = 0.84
            evidence_quality = 0.68
        elif score >= 1:
            vote = VoteValue.APPROVE
            confidence = 0.82
            evidence_quality = 0.72
        elif score <= -2:
            vote = VoteValue.DENY
            confidence = 0.86
            evidence_quality = 0.74
        elif any(term in lowered for term in conditional_terms):
            vote = VoteValue.ABSTAIN
            confidence = 0.58
            evidence_quality = 0.50
        else:
            vote = VoteValue.ABSTAIN
            confidence = 0.55
            evidence_quality = 0.45

        risk = "No major role-specific risk detected."
        condition = "Proceed with normal audit logging."
        if node.role == "Security":
            risk = "Operational exposure should be checked before execution."
            condition = "Run a security review before live deployment."
        elif node.role == "Finance":
            risk = "Cost and opportunity-cost assumptions may be incomplete."
            condition = "Attach budget ceiling and expected value estimate."
        elif node.role == "Logic":
            risk = "Proposal requires clear success criteria."
            condition = "Define measurable acceptance criteria."

        return (
            f"VOTE: {vote.value}\n"
            f"CONFIDENCE: {confidence:.2f}\n"
            f"EVIDENCE_QUALITY: {evidence_quality:.2f}\n"
            f"CRITICAL_RISK: {'true' if critical_risk else 'false'}\n"
            f"RATIONALE: {node.role} assessment based on {node.mission}. "
            f"The proposal appears {vote.value.lower()} from this perspective.\n"
            f"RISKS: {risk}\n"
            f"CONDITIONS: {condition}\n"
        )

    @staticmethod
    def _proposal_text(prompt: str) -> str:
        marker = "Proposal:"
        if marker not in prompt:
            return prompt
        section = prompt.split(marker, 1)[1]
        for stop in ("\n\nRELEVANT MEMORY CONTEXT:", "\n\nShared machine context:", "\n\nShared context:"):
            if stop in section:
                return section.split(stop, 1)[0].strip()
        return section.strip()


class OllamaBackend:
    """Optional backend for local Ollama-compatible generation."""

    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 60):
        if requests is None:
            raise RuntimeError("The requests package is required for OllamaBackend.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def list_models(self) -> List[str]:
        errors: list[str] = []
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [model.get("name", "") for model in models if model.get("name")]
        except _request_exceptions() as exc:
            errors.append(str(exc))
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=10)
            response.raise_for_status()
            models = response.json().get("data", [])
            return [model.get("id", "") for model in models if model.get("id")]
        except _request_exceptions() as exc:
            errors.append(str(exc))
            raise ProviderRequestError(f"Provider unavailable at {self.base_url}: {'; '.join(errors)}") from exc

    def complete(self, node: NodeIdentity, query: str, context: Dict[str, Any]) -> str:
        payload = {
            "model": node.model,
            "prompt": build_node_prompt(node, query, context),
            "stream": False,
            "options": {
                "temperature": node.temperature,
                "num_predict": 900,
            },
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except _request_exceptions() as exc:
            raise ProviderRequestError(f"Provider generation unavailable at {self.base_url}: {exc}") from exc


def build_backend(name: str, config: RuntimeConfig) -> LLMBackend:
    if name == "mock":
        return MockBackend()
    if name == "msty-llama-cpp":
        return OllamaBackend(base_url=os.getenv("MSTY_LLAMA_CPP_BASE_URL", config.msty_llama_cpp_base_url))
    if name == "msty-claw":
        return OllamaBackend(base_url=os.getenv("MSTY_BASE_URL", config.msty_base_url))
    if name == "msty-local":
        return OllamaBackend(base_url=os.getenv("MSTY_LLAMA_CPP_BASE_URL", config.msty_llama_cpp_base_url or "http://localhost:11454"))
    if name == "ollama":
        return OllamaBackend(base_url=os.getenv("OLLAMA_BASE_URL", config.ollama_base_url))
    raise ValueError(f"Unknown backend: {name}")
