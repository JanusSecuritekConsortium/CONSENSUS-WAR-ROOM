from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional


MSTY_ENDPOINT_ENV_VARS = (
    "AURELIUS_MSTY_BASE_URL",
    "MSTY_BASE_URL",
)
MSTY_PROVIDER_ENDPOINT_NOT_CONFIGURED = "Msty provider endpoint not configured"
OLLAMA_DISABLED_REASON = "Ollama provider is disabled for AURELIUS"


@dataclass(frozen=True)
class AureliusProviderConfig:
    provider: str
    base_url: Optional[str]
    base_url_env: Optional[str]
    endpoint_source: str
    fallback_enabled: bool
    status: str
    degraded_reason: Optional[str] = None
    requested_provider: Optional[str] = None

    @property
    def ready(self) -> bool:
        return self.status == "READY" and bool(self.base_url)

    @property
    def api_base_url(self) -> Optional[str]:
        if not self.base_url:
            return None
        base = self.base_url.rstrip("/")
        return base if base.endswith("/v1") else f"{base}/v1"

    def as_payload(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "base_url_env": self.base_url_env,
            "endpoint_source": self.endpoint_source,
            "api_base_url": self.api_base_url,
            "fallback_enabled": self.fallback_enabled,
            "status": self.status,
            "degraded_reason": self.degraded_reason,
            "requested_provider": self.requested_provider,
        }


class ProviderErrorGate:
    """Process-local once-only gate for provider errors that would spam operators."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def should_log(self, key: str) -> bool:
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


def _env_flag(environ: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _first_configured_endpoint(environ: Mapping[str, str]) -> tuple[Optional[str], Optional[str]]:
    for name in MSTY_ENDPOINT_ENV_VARS:
        value = environ.get(name)
        if value and value.strip():
            return value.strip().rstrip("/"), name
    return None, None


def _looks_like_ollama_endpoint(base_url: str) -> bool:
    lowered = base_url.lower()
    return "11434" in lowered or "ollama" in lowered


def resolve_aurelius_provider_config(
    environ: Optional[Mapping[str, str]] = None,
) -> AureliusProviderConfig:
    env = os.environ if environ is None else environ
    requested_provider = env.get("AURELIUS_PROVIDER", "msty").strip().lower() or "msty"
    fallback_enabled = _env_flag(env, "AURELIUS_PROVIDER_FALLBACK_ENABLED", default=False)
    base_url, base_url_env = _first_configured_endpoint(env)

    if requested_provider in {"ollama", "ollama-direct"}:
        reason = OLLAMA_DISABLED_REASON
        if not base_url:
            reason = f"{reason}; {MSTY_PROVIDER_ENDPOINT_NOT_CONFIGURED}"
        return AureliusProviderConfig(
            provider="msty",
            base_url=None,
            base_url_env=base_url_env,
            endpoint_source="env" if base_url_env else "default",
            fallback_enabled=fallback_enabled,
            status="DEGRADED",
            degraded_reason=reason,
            requested_provider=requested_provider,
        )

    if requested_provider != "msty":
        return AureliusProviderConfig(
            provider="msty",
            base_url=None,
            base_url_env=base_url_env,
            endpoint_source="env" if base_url_env else "default",
            fallback_enabled=fallback_enabled,
            status="DEGRADED",
            degraded_reason=f"Unsupported AURELIUS provider '{requested_provider}'; use msty",
            requested_provider=requested_provider,
        )

    if not base_url:
        return AureliusProviderConfig(
            provider="msty",
            base_url=None,
            base_url_env=None,
            endpoint_source="default",
            fallback_enabled=fallback_enabled,
            status="DEGRADED",
            degraded_reason=MSTY_PROVIDER_ENDPOINT_NOT_CONFIGURED,
            requested_provider=requested_provider,
        )

    if _looks_like_ollama_endpoint(base_url):
        return AureliusProviderConfig(
            provider="msty",
            base_url=None,
            base_url_env=base_url_env,
            endpoint_source="env",
            fallback_enabled=fallback_enabled,
            status="DEGRADED",
            degraded_reason=OLLAMA_DISABLED_REASON,
            requested_provider=requested_provider,
        )

    return AureliusProviderConfig(
        provider="msty",
        base_url=base_url,
        base_url_env=base_url_env,
        endpoint_source="env" if base_url_env else "default",
        fallback_enabled=fallback_enabled,
        status="READY",
        requested_provider=requested_provider,
    )


def scheduled_provider_error_message(config: AureliusProviderConfig) -> str:
    return config.degraded_reason or MSTY_PROVIDER_ENDPOINT_NOT_CONFIGURED
