from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from config.agents import AGENT_PROFILES
from config.names import ARBITER
from config.runtime import RuntimeConfig
from config.version import SYSTEM_VERSION
from core.history import migrate_legacy_history, result_to_dict
from core.llm.backends import OllamaBackend, ProviderRequestError
from core.logging import log_event
from core.models import NodeIdentity, TribunalResult
from core.paths import ARBITER_DIR, HISTORY_PATH, SYSTEM_ROOT
from core.themes import THEMES, resolve_theme_key
from core.tribunal import Tribunal
from core.voting.rules import ConsensusRules
from integrations.msty.runtime import MstyRuntime


MSTY_CLAW_SERVICE = "http://127.0.0.1:11964"
MSTY_LLAMA_CPP_SERVICE = "http://localhost:11454"
OLLAMA_DIRECT = "http://127.0.0.1:11434"
DEFAULT_MSTY_BASE_URL = MSTY_CLAW_SERVICE
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
BACKEND_FALLBACK_ORDER = ("msty-llama-cpp", "ollama-direct")
MODEL_CACHE_PATH = ARBITER_DIR / "provider_model_cache.json"
DEFAULT_MODEL_CACHE_TTL_SECONDS = 120
READINESS_RETRY_BACKENDS = {"msty-llama-cpp"}
DEFAULT_READINESS_RETRY_ATTEMPTS = 3
DEFAULT_READINESS_RETRY_DELAY_SECONDS = 2.0


def _canonical_backend(backend: str) -> str:
    if backend in {"ollama", "ollama-direct"}:
        return "ollama-direct"
    if backend == "msty-local":
        return "msty-llama-cpp"
    return backend


def _model_cache_ttl(config: RuntimeConfig) -> int:
    raw = os.getenv("CONSENSUS_MODEL_CACHE_TTL")
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return max(0, int(getattr(config, "model_cache_ttl_seconds", DEFAULT_MODEL_CACHE_TTL_SECONDS)))


def _readiness_retry_policy(candidate: Dict[str, str]) -> Dict[str, Any]:
    enabled = candidate.get("backend") in READINESS_RETRY_BACKENDS
    attempts = DEFAULT_READINESS_RETRY_ATTEMPTS
    delay_seconds = DEFAULT_READINESS_RETRY_DELAY_SECONDS
    raw_attempts = os.getenv("CONSENSUS_READINESS_RETRY_ATTEMPTS")
    raw_delay = os.getenv("CONSENSUS_READINESS_RETRY_DELAY_SECONDS")
    if raw_attempts:
        try:
            attempts = max(1, int(raw_attempts))
        except ValueError:
            pass
    if raw_delay:
        try:
            delay_seconds = max(0.0, float(raw_delay))
        except ValueError:
            pass
    return {"enabled": enabled, "attempts": attempts, "delay_seconds": delay_seconds}


def _readiness_meta(
    candidate: Dict[str, str],
    result: str = "NOT_NEEDED",
    warmup_retries: int = 0,
    last_error: str = "",
) -> Dict[str, Any]:
    policy = _readiness_retry_policy(candidate)
    return {
        "enabled": bool(policy["enabled"]),
        "attempts": int(policy["attempts"]),
        "delay_seconds": float(policy["delay_seconds"]),
        "result": result if policy["enabled"] else "NOT_NEEDED",
        "warmup_retries": warmup_retries,
        "last_error": last_error,
    }


def _fallback_reason_from_probe_chain(probe_chain: Iterable[Dict[str, Any]]) -> str:
    for probe in probe_chain:
        retry = probe.get("readiness_retry", {}) if isinstance(probe, dict) else {}
        if isinstance(retry, dict) and retry.get("result") == "FAILED_AFTER_RETRY":
            return "endpoint unreachable after readiness retry"
    return "endpoint unreachable"


def _readiness_summary_from_probe_chain(
    probe_chain: Iterable[Dict[str, Any]],
    default: Dict[str, Any],
) -> Dict[str, Any]:
    selected: Dict[str, Any] | None = None
    for probe in probe_chain:
        retry = probe.get("readiness_retry", {}) if isinstance(probe, dict) else {}
        if isinstance(retry, dict) and retry.get("enabled"):
            selected = retry
            if retry.get("result") in {"READY_AFTER_RETRY", "FAILED_AFTER_RETRY"}:
                return retry
    return selected or default


def _load_model_cache() -> Dict[str, Any]:
    if not MODEL_CACHE_PATH.exists():
        return {"version": 1, "entries": {}}
    try:
        payload = json.loads(MODEL_CACHE_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("entries"), dict):
            return payload
    except Exception:
        pass
    return {"version": 1, "entries": {}}


def _save_model_cache(cache: Dict[str, Any]) -> None:
    MODEL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = MODEL_CACHE_PATH.with_name(f"{MODEL_CACHE_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    tmp_path.replace(MODEL_CACHE_PATH)


def _cache_key(backend: str, endpoint: str, api_shape: str) -> str:
    return f"{backend}|{endpoint.rstrip('/')}|{api_shape or 'unknown'}"


def clear_model_cache() -> None:
    if MODEL_CACHE_PATH.exists():
        MODEL_CACHE_PATH.unlink()


def _endpoint_reachable(base_url: str, timeout: float = 1.25) -> tuple[bool, str]:
    from core.llm import backends

    if backends.requests is None:
        return True, "requests_unavailable"
    normalized = base_url.rstrip("/")
    for path in ("/health", "/v1/models", "/api/tags", "/models", "/props", "/slots", "/"):
        try:
            response = backends.requests.get(f"{normalized}{path}", timeout=timeout)
            if 200 <= response.status_code < 500 and response.status_code != 404:
                return True, f"{path}:{response.status_code}"
            last_error = f"{path}:{response.status_code}"
        except _provider_exceptions() as exc:
            last_error = str(exc)
    return False, last_error if "last_error" in locals() else "endpoint unreachable"


def validate_health_endpoint(base_url: str, timeout: float = 0.35) -> Dict[str, Any]:
    reachable, reason = _endpoint_reachable(base_url, timeout=timeout)
    return {
        "valid": reachable,
        "reason": reason,
        "checked_paths": ["/health", "/v1/models", "/api/tags", "/models", "/props", "/slots", "/"],
    }


def _retry_endpoint_reachability(candidate: Dict[str, str]) -> tuple[bool, str, Dict[str, Any]]:
    policy = _readiness_retry_policy(candidate)
    if not policy["enabled"]:
        return False, "readiness retry not enabled", _readiness_meta(candidate)
    last_reason = "endpoint unreachable"
    for attempt in range(1, int(policy["attempts"]) + 1):
        if attempt > 1 and float(policy["delay_seconds"]) > 0:
            time.sleep(float(policy["delay_seconds"]))
        reachable, reason = _endpoint_reachable(candidate["base_url"])
        last_reason = reason
        if reachable:
            return True, reason, _readiness_meta(candidate, "READY_AFTER_RETRY", attempt, reason)
    return False, last_reason, _readiness_meta(candidate, "FAILED_AFTER_RETRY", int(policy["attempts"]), last_reason)


def _enumerate_candidate_models(candidate: Dict[str, str]) -> tuple[str, list[str], str, Dict[str, Any] | None]:
    backend = OllamaBackend(base_url=candidate["base_url"])
    models = normalize_model_names(backend.list_models())
    api_shape = "ollama_compatible"
    probe_shape: Dict[str, Any] | None = None
    if not models:
        probe_shape = _probe_api_shape(candidate["base_url"])
        if probe_shape.get("reachable"):
            api_shape = ", ".join(probe_shape.get("api_shapes", []) or ["reachable_unknown"])
            models = normalize_model_names(probe_shape.get("models", []) or [])
    return backend.base_url, models, api_shape, probe_shape


def _retry_model_enumeration(candidate: Dict[str, str]) -> tuple[bool, str, list[str], str, Dict[str, Any] | None, Dict[str, Any]]:
    policy = _readiness_retry_policy(candidate)
    if not policy["enabled"]:
        return False, candidate["base_url"], [], "unknown", None, _readiness_meta(candidate)
    last_error = ""
    for attempt in range(1, int(policy["attempts"]) + 1):
        if attempt > 1 and float(policy["delay_seconds"]) > 0:
            time.sleep(float(policy["delay_seconds"]))
        try:
            base_url, models, api_shape, probe_shape = _enumerate_candidate_models(candidate)
            return True, base_url, models, api_shape, probe_shape, _readiness_meta(
                candidate,
                "READY_AFTER_RETRY",
                attempt,
                last_error,
            )
        except _provider_exceptions() as exc:
            last_error = str(exc)
    return False, candidate["base_url"], [], "unknown", None, _readiness_meta(
        candidate,
        "FAILED_AFTER_RETRY",
        int(policy["attempts"]),
        last_error,
    )


def _find_cached_model_payload(candidate: Dict[str, str], ttl_seconds: int) -> tuple[Dict[str, Any] | None, Dict[str, Any]]:
    now = time.time()
    cache = _load_model_cache()
    newest_valid: Dict[str, Any] | None = None
    stale_match: Dict[str, Any] | None = None
    for key, entry in (cache.get("entries") or {}).items():
        if entry.get("backend") != candidate["backend"] or entry.get("endpoint") != candidate["base_url"]:
            continue
        age = now - float(entry.get("timestamp", 0))
        entry = dict(entry)
        entry["cache_key"] = key
        entry["cache_age_seconds"] = round(age, 2)
        entry["ttl_seconds"] = ttl_seconds
        if age <= ttl_seconds:
            if newest_valid is None or float(entry.get("timestamp", 0)) > float(newest_valid.get("timestamp", 0)):
                newest_valid = entry
        elif stale_match is None or float(entry.get("timestamp", 0)) > float(stale_match.get("timestamp", 0)):
            stale_match = entry
    if newest_valid:
        return newest_valid, {
            "cache_status": "hit",
            "cache_age_seconds": newest_valid.get("cache_age_seconds"),
            "stale_cache": None,
        }
    return None, {
        "cache_status": "miss",
        "cache_reason": "expired" if stale_match else "absent",
        "stale_cache": stale_match,
    }


def _write_model_payload_cache(
    candidate: Dict[str, str],
    api_shape: str,
    models: list[str],
    latency_ms: float,
    ttl_seconds: int,
) -> Dict[str, Any]:
    now = time.time()
    cache = _load_model_cache()
    entries = {
        key: value
        for key, value in dict(cache.get("entries") or {}).items()
        if not (value.get("backend") == candidate["backend"] and value.get("endpoint") == candidate["base_url"])
    }
    key = _cache_key(candidate["backend"], candidate["base_url"], api_shape)
    entry = {
        "backend": candidate["backend"],
        "endpoint": candidate["base_url"],
        "api_shape": api_shape,
        "model_source": candidate["backend"],
        "models": models,
        "alias_matches": {},
        "timestamp": now,
        "ttl_seconds": ttl_seconds,
        "latency_ms_original": latency_ms,
        "from_cache": False,
    }
    entries[key] = entry
    _save_model_cache({"version": 1, "entries": entries})
    return entry


def _update_model_cache_alias_matches(backend: str, endpoint: str, api_shape: str, alias_matches: Dict[str, Any]) -> None:
    if not alias_matches:
        return
    cache = _load_model_cache()
    entries = dict(cache.get("entries") or {})
    key = _cache_key(backend, endpoint, api_shape)
    if key not in entries:
        for candidate_key, entry in entries.items():
            if entry.get("backend") == backend and entry.get("endpoint") == endpoint:
                key = candidate_key
                break
    if key in entries:
        entry = dict(entries[key])
        entry["alias_matches"] = alias_matches
        entries[key] = entry
        _save_model_cache({"version": 1, "entries": entries})


def _provider_exceptions() -> tuple[type[BaseException], ...]:
    from core.llm import backends

    if backends.requests is None:
        return (ProviderRequestError, RuntimeError)
    return (
        ProviderRequestError,
        RuntimeError,
        backends.requests.ConnectionError,
        backends.requests.Timeout,
        backends.requests.RequestException,
    )


def _provider_candidates(config: Optional[RuntimeConfig] = None) -> list[Dict[str, str]]:
    runtime_config = config or RuntimeConfig()
    candidates: list[Dict[str, str]] = []

    def add(source: str, backend: str, base_url: Optional[str]) -> None:
        if not base_url:
            return
        candidate = {"source": source, "backend": backend, "base_url": base_url.rstrip("/")}
        if not any(
            item["backend"] == candidate["backend"] and item["base_url"] == candidate["base_url"]
            for item in candidates
        ):
            candidates.append(candidate)

    if runtime_config.backend == "mock":
        return [{"source": "config_backend", "backend": "mock", "base_url": ""}]

    def add_backend(backend: str) -> None:
        if backend == "msty-claw":
            add("config_msty_claw", "msty-claw", runtime_config.msty_base_url)
            add("env_msty_claw", "msty-claw", os.getenv("MSTY_BASE_URL"))
            add("default_msty_claw_service", "msty-claw", MSTY_CLAW_SERVICE)
        elif backend == "msty-llama-cpp":
            add("config_msty_llama_cpp", "msty-llama-cpp", runtime_config.msty_llama_cpp_base_url)
            add("env_msty_llama_cpp", "msty-llama-cpp", os.getenv("MSTY_LLAMA_CPP_BASE_URL"))
            add("default_msty_llama_cpp", "msty-llama-cpp", MSTY_LLAMA_CPP_SERVICE)
        elif backend == "ollama-direct":
            add("config_ollama", "ollama-direct", runtime_config.ollama_base_url)
            add("env_ollama", "ollama-direct", os.getenv("OLLAMA_BASE_URL"))
            add("default_ollama_direct", "ollama-direct", OLLAMA_DIRECT)

    requested_backend = _canonical_backend(runtime_config.backend)
    backend_order = [requested_backend]
    backend_order.extend(backend for backend in BACKEND_FALLBACK_ORDER if backend != requested_backend)
    for backend in backend_order:
        add_backend(backend)
    return candidates


def resolve_provider(config: Optional[RuntimeConfig] = None) -> Dict[str, Any]:
    runtime_config = config or RuntimeConfig()
    candidates = _provider_candidates(runtime_config)
    concrete_candidates = [candidate for candidate in candidates if candidate.get("base_url")]
    requested_backend = _canonical_backend(runtime_config.backend)
    requested_endpoint = concrete_candidates[0]["base_url"] if concrete_candidates else DEFAULT_MSTY_BASE_URL
    return {
        "provider": "msty",
        "requested_backend": requested_backend,
        "requested_endpoint": requested_endpoint,
        "candidate_priority": candidates,
        "default_backend": _canonical_backend(RuntimeConfig().backend),
        "mock_selected": runtime_config.backend == "mock",
    }


def resolve_provider_base_url(config: Optional[RuntimeConfig] = None) -> str:
    resolution = resolve_provider(config)
    return str(resolution.get("requested_endpoint") or DEFAULT_MSTY_BASE_URL)


def required_model_map(
    nodes: Optional[Dict[str, NodeIdentity]] = None,
    config: Optional[RuntimeConfig] = None,
) -> Dict[str, str]:
    overrides = (config.agent_model_overrides if config else {}) or {}
    required = {ARBITER: overrides.get(ARBITER, AGENT_PROFILES[ARBITER].model_preference)}
    if nodes:
        required.update({agent_id: overrides.get(agent_id, node.model) for agent_id, node in nodes.items()})
    return required


def normalize_model_names(models: Iterable[Any]) -> list[str]:
    names: list[str] = []
    for model in models:
        candidate = ""
        if isinstance(model, str) and model:
            candidate = model
        elif isinstance(model, dict) and model.get("name"):
            candidate = str(model["name"])
        elif isinstance(model, dict) and model.get("id"):
            candidate = str(model["id"])
        elif isinstance(model, dict) and model.get("model"):
            candidate = str(model["model"])
        if candidate and candidate.strip().lower() not in {"none", "null", "unknown"}:
            names.append(candidate)
    return names


def _models_from_payload(payload: Any) -> tuple[list[str], str]:
    if isinstance(payload, list):
        return normalize_model_names(payload), "list"
    if not isinstance(payload, dict):
        return [], "unknown"
    for key, schema in (
        ("models", "ollama_models"),
        ("data", "openai_models"),
        ("slots", "llama_cpp_slots"),
        ("model_path", "llama_cpp_props"),
        ("model_alias", "llama_cpp_props"),
        ("model_name", "llama_cpp_props"),
        ("model", "single_model"),
        ("name", "single_name"),
        ("id", "single_id"),
    ):
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, list):
            return normalize_model_names(value), schema
        if isinstance(value, str):
            return [value], schema
    nested = payload.get("result") or payload.get("response")
    if isinstance(nested, (dict, list)):
        return _models_from_payload(nested)
    return [], "json_no_models"


def normalize_model_alias(model_name: str) -> str:
    normalized = model_name.lower().strip()
    for suffix in (":latest", ".gguf", "-gguf", "_gguf", ".q4_k_s", "-q4_k_s", "_q4_k_s", ".q4", "-q4", "_q4"):
        normalized = normalized.replace(suffix, "")
    return "".join(character for character in normalized if character.isalnum())


def match_model_alias(required_model: str, available_models: Iterable[str]) -> tuple[Optional[str], str]:
    available = list(available_models)
    if required_model in available:
        return required_model, "exact"
    required_key = normalize_model_alias(required_model)
    for model in available:
        if normalize_model_alias(model) == required_key:
            return model, "normalized"
    for model in available:
        model_key = normalize_model_alias(model)
        if len(required_key) >= 4 and len(model_key) >= 4 and (
            required_key.startswith(model_key)
            or model_key.startswith(required_key)
            or required_key in model_key
            or model_key in required_key
        ):
            return model, "alias"
    return None, "missing"


def resolve_required_model_aliases(
    required: Dict[str, str],
    available_models: Iterable[str],
) -> tuple[Dict[str, str], Dict[str, str], Dict[str, Dict[str, str]]]:
    models = list(available_models)
    missing: Dict[str, str] = {}
    resolved: Dict[str, str] = {}
    alias_matches: Dict[str, Dict[str, str]] = {}
    for agent_id, configured_model in required.items():
        matched_model, match_type = match_model_alias(configured_model, models)
        if matched_model:
            resolved[agent_id] = matched_model
            if matched_model != configured_model or match_type != "exact":
                alias_matches[agent_id] = {
                    "configured": configured_model,
                    "resolved": matched_model,
                    "match_type": match_type,
                }
        else:
            missing[agent_id] = configured_model
    return missing, resolved, alias_matches


def model_availability_report(
    required: Dict[str, str],
    available_models: Iterable[str],
    resolved_required: Optional[Dict[str, str]] = None,
    remapped_model: Optional[str] = None,
) -> list[Dict[str, Any]]:
    models = list(available_models)
    resolved = dict(resolved_required or {})
    report: list[Dict[str, Any]] = []
    for agent_id, configured_model in required.items():
        resolved_model = resolved.get(agent_id)
        if resolved_model:
            status = "remapped" if remapped_model and resolved_model == remapped_model and configured_model != remapped_model else "ready"
            match_type = "resolved"
        else:
            matched_model, match_type = match_model_alias(configured_model, models)
            resolved_model = matched_model
            status = "ready" if matched_model else "missing"
        report.append(
            {
                "agent_id": agent_id,
                "required_model": configured_model,
                "resolved_model": resolved_model,
                "status": status,
                "match_type": match_type,
            }
        )
    return report


def list_models(config: Optional[RuntimeConfig] = None) -> Dict[str, Any]:
    runtime_config = config or RuntimeConfig()
    requested_backend = _canonical_backend(runtime_config.backend)
    ttl_seconds = _model_cache_ttl(runtime_config)
    if runtime_config.backend == "mock":
        return {
            "backend": "mock",
            "active_backend": "mock",
            "requested_backend": "mock",
            "requested_endpoint": None,
            "requested_backend_status": "ready",
            "fallback_active": False,
            "fallback_reason": None,
            "probe_chain": [],
            "status": "ready",
            "base_url": None,
            "models": ["mock"],
            "model_count": 1,
            "latency_ms": 0,
            "model_cache": {"status": "bypass", "reason": "mock_backend", "ttl_seconds": ttl_seconds},
            "readiness_retry": {"enabled": False, "attempts": 0, "delay_seconds": 0.0, "result": "NOT_NEEDED", "warmup_retries": 0},
            "from_cache": False,
        }

    resolution = resolve_provider(runtime_config)
    candidates = [candidate for candidate in resolution["candidate_priority"] if candidate.get("base_url")]
    first_endpoint = str(resolution["requested_endpoint"])
    last_error = ""
    probe_chain: list[Dict[str, Any]] = []
    requested_probe: Dict[str, Any] | None = None
    for candidate in candidates:
        started = time.perf_counter()
        if not runtime_config.refresh_model_cache and ttl_seconds > 0:
            readiness_meta = _readiness_meta(candidate)
            cached, cache_meta = _find_cached_model_payload(candidate, ttl_seconds)
            if cached:
                reachable, reachability_reason = _endpoint_reachable(candidate["base_url"])
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                if not reachable and _readiness_retry_policy(candidate)["enabled"]:
                    retry_reachable, retry_reason, readiness_meta = _retry_endpoint_reachability(candidate)
                    if retry_reachable:
                        reachable = True
                        reachability_reason = retry_reason
                        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                if reachable:
                    probe_entry = {
                        "backend": candidate["backend"],
                        "base_url": candidate["base_url"],
                        "source": candidate["source"],
                        "status": "ready",
                        "latency_ms": elapsed_ms,
                        "model_count": len(cached.get("models", []) or []),
                        "error": None,
                        "health_endpoint": {"valid": True, "reason": reachability_reason},
                        "readiness_retry": _readiness_summary_from_probe_chain(probe_chain, readiness_meta),
                    }
                    probe_chain.append(probe_entry)
                    if requested_probe is None and candidate["backend"] == requested_backend:
                        requested_probe = probe_entry
                    fallback_active = candidate["backend"] != requested_backend or candidate["base_url"] != first_endpoint
                    return {
                        "backend": candidate["backend"],
                        "active_backend": candidate["backend"],
                        "requested_backend": requested_backend,
                        "requested_endpoint": first_endpoint,
                        "requested_backend_status": (requested_probe or probe_entry)["status"],
                        "source": candidate["source"],
                        "status": "ready",
                        "base_url": candidate["base_url"],
                        "models": list(cached.get("models", []) or []),
                        "model_count": len(cached.get("models", []) or []),
                        "latency_ms": elapsed_ms,
                        "fallback_active": fallback_active,
                        "fallback_reason": _fallback_reason_from_probe_chain(probe_chain) if fallback_active else None,
                        "probe_chain": probe_chain,
                        "api_shape": str(cached.get("api_shape") or "cached"),
                        "model_source": str(cached.get("model_source") or candidate["backend"]),
                        "raw_routes": [],
                        "model_cache": {
                            "status": "hit",
                            "age_seconds": cache_meta.get("cache_age_seconds"),
                            "ttl_seconds": ttl_seconds,
                            "latency_ms_original": cached.get("latency_ms_original"),
                            "current_check_latency_ms": elapsed_ms,
                            "reason": reachability_reason,
                        },
                        "readiness_retry": _readiness_summary_from_probe_chain(probe_chain, readiness_meta),
                        "from_cache": True,
                    }
                probe_chain.append(
                    {
                        "backend": candidate["backend"],
                        "base_url": candidate["base_url"],
                        "source": candidate["source"],
                        "status": "offline",
                        "latency_ms": elapsed_ms,
                        "model_count": 0,
                        "error": reachability_reason,
                        "stale_cache_available": True,
                        "stale_cache_age_seconds": cache_meta.get("cache_age_seconds"),
                        "readiness_retry": readiness_meta,
                    }
                )
                last_error = reachability_reason
                continue
        try:
            readiness_meta = _readiness_meta(candidate)
            base_url, models, api_shape, probe_shape = _enumerate_candidate_models(candidate)
            health_endpoint = (
                {
                    "valid": True,
                    "reason": f"{api_shape}:models_enumerated",
                    "checked_paths": ["/v1/models", "/api/tags", "/models", "/props", "/slots"],
                }
                if models
                else validate_health_endpoint(base_url)
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            if not models and probe_shape and probe_shape.get("reachable"):
                probe_entry = {
                    "backend": candidate["backend"],
                    "base_url": base_url,
                    "source": candidate["source"],
                    "status": "degraded",
                    "latency_ms": elapsed_ms,
                    "model_count": 0,
                    "error": "models_not_enumerated",
                    "health_endpoint": health_endpoint,
                    "readiness_retry": _readiness_summary_from_probe_chain(probe_chain, readiness_meta),
                }
                probe_chain.append(probe_entry)
                if requested_probe is None and candidate["backend"] == requested_backend:
                    requested_probe = probe_entry
                fallback_active = candidate["backend"] != requested_backend or base_url != first_endpoint
                return {
                    "backend": candidate["backend"],
                    "active_backend": candidate["backend"],
                    "requested_backend": requested_backend,
                    "requested_endpoint": first_endpoint,
                    "requested_backend_status": (requested_probe or probe_entry)["status"],
                    "source": candidate["source"],
                    "status": "degraded",
                    "base_url": base_url,
                    "models": [],
                    "model_count": 0,
                    "latency_ms": elapsed_ms,
                    "fallback_active": fallback_active,
                    "fallback_reason": _fallback_reason_from_probe_chain(probe_chain) if fallback_active else None,
                    "probe_chain": probe_chain,
                    "api_shape": api_shape,
                    "model_source": candidate["backend"],
                    "degraded_reason": "models_not_enumerated",
                    "raw_routes": probe_shape.get("raw_routes", []),
                    "health_endpoint": health_endpoint,
                    "model_cache": {
                        "status": "miss",
                        "reason": "forced_refresh" if runtime_config.refresh_model_cache else "models_not_enumerated",
                        "ttl_seconds": ttl_seconds,
                    },
                    "readiness_retry": _readiness_summary_from_probe_chain(probe_chain, readiness_meta),
                    "from_cache": False,
                }
            probe_entry = {
                "backend": candidate["backend"],
                "base_url": base_url,
                "source": candidate["source"],
                "status": "ready",
                "latency_ms": elapsed_ms,
                "model_count": len(models),
                "error": None,
                "health_endpoint": health_endpoint,
                "readiness_retry": _readiness_summary_from_probe_chain(probe_chain, readiness_meta),
            }
            probe_chain.append(probe_entry)
            if requested_probe is None and candidate["backend"] == requested_backend:
                requested_probe = probe_entry
            fallback_active = candidate["backend"] != requested_backend or base_url != first_endpoint
            if fallback_active:
                log_event(
                    "provider_runtime_switch",
                    {
                        "requested_backend": requested_backend,
                        "active_backend": candidate["backend"],
                        "base_url": candidate["base_url"],
                        "source": candidate["source"],
                        "fallback_reason": _fallback_reason_from_probe_chain(probe_chain),
                    },
                    level="INFO",
                )
            cache_entry = _write_model_payload_cache(candidate, api_shape, models, elapsed_ms, ttl_seconds)
            return {
                "backend": candidate["backend"],
                "active_backend": candidate["backend"],
                "requested_backend": requested_backend,
                "requested_endpoint": first_endpoint,
                "requested_backend_status": (requested_probe or probe_entry)["status"],
                "source": candidate["source"],
                "status": "ready",
                "base_url": base_url,
                "models": models,
                "model_count": len(models),
                "latency_ms": elapsed_ms,
                "fallback_active": fallback_active,
                "fallback_reason": _fallback_reason_from_probe_chain(probe_chain) if fallback_active else None,
                "probe_chain": probe_chain,
                "api_shape": api_shape,
                "model_source": candidate["backend"],
                "raw_routes": probe_shape.get("raw_routes", []) if probe_shape else [],
                "health_endpoint": health_endpoint,
                "model_cache": {
                    "status": "refresh" if runtime_config.refresh_model_cache else "miss",
                    "reason": "forced_refresh" if runtime_config.refresh_model_cache else "absent_or_expired",
                    "ttl_seconds": ttl_seconds,
                    "latency_ms_original": cache_entry.get("latency_ms_original"),
                    "current_check_latency_ms": elapsed_ms,
                },
                "readiness_retry": _readiness_summary_from_probe_chain(probe_chain, readiness_meta),
                "from_cache": False,
            }
        except _provider_exceptions() as exc:
            last_error = str(exc)
            readiness_meta = _readiness_meta(candidate, "WARMING_UP", 0, last_error)
            if _readiness_retry_policy(candidate)["enabled"]:
                probe_chain.append(
                    {
                        "backend": candidate["backend"],
                        "base_url": candidate["base_url"],
                        "source": candidate["source"],
                        "status": "warming_up",
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                        "model_count": 0,
                        "error": str(exc),
                        "readiness_retry": _readiness_summary_from_probe_chain(probe_chain, readiness_meta),
                    }
                )
                retry_ready, retry_base_url, retry_models, retry_api_shape, retry_probe_shape, readiness_meta = _retry_model_enumeration(candidate)
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                if retry_ready:
                    retry_health_endpoint = (
                        {
                            "valid": True,
                            "reason": f"{retry_api_shape}:models_enumerated",
                            "checked_paths": ["/v1/models", "/api/tags", "/models", "/props", "/slots"],
                        }
                        if retry_models
                        else validate_health_endpoint(retry_base_url)
                    )
                    if not retry_models and retry_probe_shape and retry_probe_shape.get("reachable"):
                        probe_entry = {
                            "backend": candidate["backend"],
                            "base_url": retry_base_url,
                            "source": candidate["source"],
                            "status": "degraded",
                            "latency_ms": elapsed_ms,
                            "model_count": 0,
                            "error": "models_not_enumerated",
                            "health_endpoint": retry_health_endpoint,
                            "readiness_retry": readiness_meta,
                        }
                        probe_chain.append(probe_entry)
                        if requested_probe is None and candidate["backend"] == requested_backend:
                            requested_probe = probe_entry
                        fallback_active = candidate["backend"] != requested_backend or retry_base_url != first_endpoint
                        return {
                            "backend": candidate["backend"],
                            "active_backend": candidate["backend"],
                            "requested_backend": requested_backend,
                            "requested_endpoint": first_endpoint,
                            "requested_backend_status": (requested_probe or probe_entry)["status"],
                            "source": candidate["source"],
                            "status": "degraded",
                            "base_url": retry_base_url,
                            "models": [],
                            "model_count": 0,
                            "latency_ms": elapsed_ms,
                            "fallback_active": fallback_active,
                            "fallback_reason": _fallback_reason_from_probe_chain(probe_chain) if fallback_active else None,
                            "probe_chain": probe_chain,
                            "api_shape": retry_api_shape,
                            "model_source": candidate["backend"],
                            "degraded_reason": "models_not_enumerated",
                            "raw_routes": retry_probe_shape.get("raw_routes", []),
                            "health_endpoint": retry_health_endpoint,
                            "model_cache": {
                                "status": "miss",
                                "reason": "forced_refresh" if runtime_config.refresh_model_cache else "models_not_enumerated",
                                "ttl_seconds": ttl_seconds,
                            },
                            "readiness_retry": readiness_meta,
                            "from_cache": False,
                        }
                    probe_entry = {
                        "backend": candidate["backend"],
                        "base_url": retry_base_url,
                        "source": candidate["source"],
                        "status": "ready",
                        "latency_ms": elapsed_ms,
                        "model_count": len(retry_models),
                        "error": None,
                        "health_endpoint": retry_health_endpoint,
                        "readiness_retry": _readiness_summary_from_probe_chain(probe_chain, readiness_meta),
                    }
                    probe_chain.append(probe_entry)
                    if requested_probe is None and candidate["backend"] == requested_backend:
                        requested_probe = probe_entry
                    fallback_active = candidate["backend"] != requested_backend or retry_base_url != first_endpoint
                    cache_entry = _write_model_payload_cache(candidate, retry_api_shape, retry_models, elapsed_ms, ttl_seconds)
                    return {
                        "backend": candidate["backend"],
                        "active_backend": candidate["backend"],
                        "requested_backend": requested_backend,
                        "requested_endpoint": first_endpoint,
                        "requested_backend_status": (requested_probe or probe_entry)["status"],
                        "source": candidate["source"],
                        "status": "ready",
                        "base_url": retry_base_url,
                        "models": retry_models,
                        "model_count": len(retry_models),
                        "latency_ms": elapsed_ms,
                        "fallback_active": fallback_active,
                        "fallback_reason": _fallback_reason_from_probe_chain(probe_chain) if fallback_active else None,
                        "probe_chain": probe_chain,
                        "api_shape": retry_api_shape,
                        "model_source": candidate["backend"],
                        "raw_routes": retry_probe_shape.get("raw_routes", []) if retry_probe_shape else [],
                        "health_endpoint": retry_health_endpoint,
                        "model_cache": {
                            "status": "refresh" if runtime_config.refresh_model_cache else "miss",
                            "reason": "forced_refresh" if runtime_config.refresh_model_cache else "absent_or_expired",
                            "ttl_seconds": ttl_seconds,
                            "latency_ms_original": cache_entry.get("latency_ms_original"),
                            "current_check_latency_ms": elapsed_ms,
                        },
                        "readiness_retry": readiness_meta,
                        "from_cache": False,
                    }
                last_error = readiness_meta.get("last_error") or last_error
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            probe_entry = {
                "backend": candidate["backend"],
                "base_url": candidate["base_url"],
                "source": candidate["source"],
                "status": "offline",
                "latency_ms": elapsed_ms,
                "model_count": 0,
                "error": last_error or str(exc),
                "readiness_retry": readiness_meta,
            }
            probe_chain.append(probe_entry)
            if requested_probe is None and candidate["backend"] == requested_backend:
                requested_probe = probe_entry
            log_event(
                "provider_probe_unreachable",
                {
                    "requested_backend": requested_backend,
                    "candidate_backend": candidate["backend"],
                    "base_url": candidate["base_url"],
                    "source": candidate["source"],
                    "error": last_error or str(exc),
                },
                level="WARN",
            )

    if last_error:
        log_event(
            "provider_model_list_offline",
            {"backend": runtime_config.backend, "base_url": first_endpoint, "error": last_error},
            level="WARN",
        )
    return {
        "backend": requested_backend,
        "active_backend": requested_backend,
        "requested_backend": requested_backend,
        "requested_endpoint": first_endpoint,
        "requested_backend_status": (requested_probe or {}).get("status", "offline"),
        "status": "offline",
        "base_url": first_endpoint,
        "models": [],
        "model_count": 0,
        "latency_ms": None,
        "error": last_error or "provider offline",
        "fallback_active": False,
        "fallback_reason": None,
        "probe_chain": probe_chain,
        "api_shape": "unknown",
        "model_source": None,
        "model_cache": {
            "status": "miss",
            "reason": "backend_unreachable",
            "ttl_seconds": ttl_seconds,
        },
        "readiness_retry": (requested_probe or {}).get("readiness_retry", {}),
        "from_cache": False,
    }


def _probe_api_shape(base_url: str) -> Dict[str, Any]:
    from core.llm import backends

    normalized = base_url.rstrip("/")
    result: Dict[str, Any] = {
        "base_url": normalized,
        "reachable": False,
        "api_shapes": [],
        "models": [],
        "model_count": 0,
        "errors": {},
        "raw_routes": [],
    }
    if backends.requests is None:
        result["errors"]["requests"] = "requests package unavailable"
        return result

    probes = {
        "/": "root",
        "/v1/models": "openai_models",
        "/v1/chat/completions": "openai_chat",
        "/v1/completions": "openai_completions",
        "/models": "models",
        "/api/tags": "ollama_tags",
        "/api/models": "api_models",
        "/api/generate": "ollama_generate",
        "/props": "llama_cpp_props",
        "/slots": "llama_cpp_slots",
        "/health": "health",
        "/docs": "docs",
        "/openapi.json": "openapi",
    }
    for path, shape in probes.items():
        route: Dict[str, Any] = {
            "path": path,
            "status_code": None,
            "content_type": "",
            "detected_schema": "none",
            "models": [],
            "rejection_reason": "",
        }
        try:
            response = backends.requests.get(f"{normalized}{path}", timeout=3)
            route["status_code"] = response.status_code
            route["content_type"] = response.headers.get("content-type", "")
            response.raise_for_status()
            result["reachable"] = True
            if "json" in str(route["content_type"]).lower():
                payload = response.json()
                models, schema = _models_from_payload(payload)
                route["detected_schema"] = schema
            else:
                body = response.text.strip()
                models = [body] if path not in {"/", "/health"} and 0 < len(body) <= 160 else []
                route["detected_schema"] = shape if path in {"/docs"} else "non_json"
                route["rejection_reason"] = "" if models else "non_json_response"
            if models:
                result["api_shapes"].append(shape)
            result["models"].extend(model for model in models if model not in result["models"])
            route["models"] = models
        except _provider_exceptions() as exc:
            result["errors"][path] = str(exc)
            route["rejection_reason"] = str(exc)
        except ValueError as exc:
            result["errors"][path] = f"invalid json: {exc}"
            route["rejection_reason"] = f"invalid json: {exc}"
        finally:
            result["raw_routes"].append(route)
    result["model_count"] = len(result["models"])
    return result


def provider_diagnostics(config: Optional[RuntimeConfig] = None) -> Dict[str, Any]:
    runtime_config = config or RuntimeConfig()
    endpoints: list[Dict[str, str]] = [
        {
            "name": "MSTY_CLAW_SERVICE",
            "backend": "msty-claw",
            "base_url": MSTY_CLAW_SERVICE,
            "role": "Msty Claw / tool orchestration bridge",
        },
        {
            "name": "MSTY_LLAMA_CPP_SERVICE",
            "backend": "msty-llama-cpp",
            "base_url": MSTY_LLAMA_CPP_SERVICE,
            "role": "local model inference runtime",
        },
        {
            "name": "OLLAMA_DIRECT",
            "backend": "ollama-direct",
            "base_url": OLLAMA_DIRECT,
            "role": "lowest-priority Ollama direct fallback runtime",
        },
    ]

    def add(name: str, backend: str, base_url: Optional[str], role: str) -> None:
        if not base_url:
            return
        normalized = base_url.rstrip("/")
        if any(item["base_url"] == normalized and item["name"] == name for item in endpoints):
            return
        endpoints.append({"name": name, "backend": backend, "base_url": normalized, "role": role})

    add("EXPLICIT_MSTY_CLAW_BASE_URL", "msty-claw", os.getenv("MSTY_BASE_URL"), "explicit Msty Claw override")
    add("CONFIGURED_MSTY_CLAW_BASE_URL", "msty-claw", runtime_config.msty_base_url, "configured Msty Claw endpoint")
    add("EXPLICIT_OLLAMA_BASE_URL", "ollama-direct", os.getenv("OLLAMA_BASE_URL"), "explicit Ollama override")
    add("CONFIGURED_OLLAMA_BASE_URL", "ollama-direct", runtime_config.ollama_base_url, "configured Ollama endpoint")
    add(
        "EXPLICIT_MSTY_LLAMA_CPP_BASE_URL",
        "msty-llama-cpp",
        os.getenv("MSTY_LLAMA_CPP_BASE_URL"),
        "explicit LLaMA.cpp override",
    )
    add(
        "CONFIGURED_MSTY_LLAMA_CPP_BASE_URL",
        "msty-llama-cpp",
        runtime_config.msty_llama_cpp_base_url,
        "configured LLaMA.cpp endpoint",
    )

    diagnostics = []
    seen_urls: set[str] = set()
    for endpoint in endpoints:
        key = f"{endpoint['name']}|{endpoint['base_url']}"
        if key in seen_urls:
            continue
        seen_urls.add(key)
        shape = _probe_api_shape(endpoint["base_url"])
        classification = _classify_service(endpoint["backend"], shape)
        diagnostics.append({**endpoint, **shape, **classification})
    return {"endpoints": diagnostics, "candidate_priority": resolve_provider(runtime_config)["candidate_priority"]}


def _classify_service(backend: str, shape: Dict[str, Any]) -> Dict[str, str]:
    if not shape.get("reachable"):
        return {"service_classification": "unknown", "model_inference": "offline"}
    inference_shapes = {
        "openai_models",
        "ollama_tags",
        "models",
        "api_models",
        "llama_cpp_props",
        "llama_cpp_slots",
        "single_model",
    }
    inference_capable = bool(set(shape.get("api_shapes", [])) & inference_shapes) and bool(shape.get("models"))
    if backend == "msty-claw":
        return {
            "service_classification": "inference_capable" if inference_capable else "tool_bridge",
            "model_inference": "compatible" if inference_capable else "optional / not assumed",
        }
    if backend == "msty-llama-cpp":
        return {
            "service_classification": "inference_runtime" if inference_capable else "unknown",
            "model_inference": "expected" if inference_capable else "expected but not enumerated",
        }
    if backend == "ollama-direct":
        return {
            "service_classification": "inference_runtime" if inference_capable else "unknown",
            "model_inference": "expected" if inference_capable else "expected but not enumerated",
        }
    return {"service_classification": "unknown", "model_inference": "unknown"}


def send_prompt(
    model: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    config: Optional[RuntimeConfig] = None,
    base_url: Optional[str] = None,
) -> str:
    runtime_config = config or RuntimeConfig()
    backend = OllamaBackend(base_url=base_url or resolve_provider_base_url(runtime_config))
    full_prompt = f"{system_prompt.strip()}\n\n{prompt}" if system_prompt else prompt
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 900},
    }
    response = backend_requests_post(backend, payload)
    return response.get("response", "")


def health_check(
    config: Optional[RuntimeConfig] = None,
    nodes: Optional[Dict[str, NodeIdentity]] = None,
) -> Dict[str, Any]:
    runtime_config = config or RuntimeConfig()
    required = required_model_map(nodes, runtime_config)
    if runtime_config.backend == "mock":
        return {
            "backend": "mock",
            "active_backend": "mock",
            "requested_backend": "mock",
            "requested_endpoint": None,
            "requested_backend_status": "ready",
            "status": "ready",
            "base_url": None,
            "models": ["mock"],
            "latency_ms": 0,
            "model_count": 1,
            "required_models": required,
            "missing_required_models": {},
            "model_status": {agent_id: "mock" for agent_id in required},
            "model_availability_report": model_availability_report(required, ["mock"], required),
            "mode": "READY",
            "degraded_reason": None,
            "model_remap_active": False,
            "model_remap_model": None,
            "resolved_required_models": required,
            "model_alias_matches": {},
            "fallback_active": False,
            "fallback_reason": None,
            "probe_chain": [],
            "api_shape": "mock",
            "model_source": "mock",
            "model_cache": {"status": "bypass", "reason": "mock_backend", "ttl_seconds": _model_cache_ttl(runtime_config)},
            "readiness_retry": {"enabled": False, "attempts": 0, "delay_seconds": 0.0, "result": "NOT_NEEDED", "warmup_retries": 0},
            "from_cache": False,
            "mock_fallback_enabled": runtime_config.mock_fallback_enabled,
            "strict_provider_mode": runtime_config.strict_provider_mode,
        }
    try:
        model_payload = list_models(runtime_config)
        if model_payload.get("status") == "offline":
            return {
                "backend": model_payload.get("active_backend", runtime_config.backend),
                "active_backend": model_payload.get("active_backend", runtime_config.backend),
                "requested_backend": model_payload.get("requested_backend", _canonical_backend(runtime_config.backend)),
                "requested_endpoint": model_payload.get("requested_endpoint"),
                "requested_backend_status": model_payload.get("requested_backend_status", "offline"),
                "status": "offline",
                "base_url": model_payload["base_url"],
                "models": [],
                "latency_ms": model_payload["latency_ms"],
                "model_count": 0,
                "required_models": required,
                "missing_required_models": required,
                "model_status": {agent_id: "offline" for agent_id in required},
                "model_availability_report": model_availability_report(required, []),
                "mode": "OFFLINE",
                "degraded_reason": model_payload.get("degraded_reason"),
                "model_remap_active": False,
                "model_remap_model": None,
                "resolved_required_models": {},
                "model_alias_matches": {},
                "fallback_active": runtime_config.mock_fallback_enabled,
                "fallback_reason": model_payload.get("fallback_reason") or "endpoint unreachable",
                "probe_chain": model_payload.get("probe_chain", []),
                "api_shape": model_payload.get("api_shape", "unknown"),
                "model_source": model_payload.get("model_source"),
                "health_endpoint": model_payload.get("health_endpoint", {}),
                "model_cache": model_payload.get("model_cache", {}),
                "readiness_retry": model_payload.get("readiness_retry", {}),
                "from_cache": bool(model_payload.get("from_cache")),
                "mock_fallback_enabled": runtime_config.mock_fallback_enabled,
                "strict_provider_mode": runtime_config.strict_provider_mode,
                "error": model_payload.get("error", "provider offline"),
            }
        models = normalize_model_names(model_payload["models"])
        missing, resolved_required, alias_matches = resolve_required_model_aliases(required, models)
        remap_model = models[0] if models and missing and runtime_config.use_available_model_fallback else None
        effective_required_models = dict(resolved_required)
        if remap_model:
            for agent_id in missing:
                effective_required_models[agent_id] = remap_model
        availability_report = model_availability_report(
            required,
            models,
            effective_required_models,
            remapped_model=remap_model,
        )
        _update_model_cache_alias_matches(
            str(model_payload.get("active_backend") or model_payload.get("backend")),
            str(model_payload.get("base_url") or ""),
            str(model_payload.get("api_shape") or "unknown"),
            alias_matches,
        )
        status = "ready" if not missing else "degraded"
        mode = "READY" if not missing else ("DEGRADED_MODEL_REMAP" if remap_model else "DEGRADED")
        if remap_model:
            log_event(
                "model_remap_active",
                {
                    "model": remap_model,
                    "active_backend": model_payload.get("active_backend", model_payload.get("backend")),
                    "missing_required_models": missing,
                },
                level="WARN",
            )
        return {
            "backend": model_payload.get("active_backend", model_payload["backend"]),
            "active_backend": model_payload.get("active_backend", model_payload["backend"]),
            "requested_backend": model_payload.get("requested_backend", _canonical_backend(runtime_config.backend)),
            "requested_endpoint": model_payload.get("requested_endpoint"),
            "requested_backend_status": model_payload.get("requested_backend_status"),
            "source": model_payload.get("source"),
            "status": status,
            "base_url": model_payload["base_url"],
            "models": models,
            "latency_ms": model_payload["latency_ms"],
            "model_count": len(models),
            "required_models": required,
            "missing_required_models": missing,
            "resolved_required_models": effective_required_models,
            "model_alias_matches": alias_matches,
            "model_status": {
                agent_id: "remapped" if remap_model and agent_id in missing else ("missing" if agent_id in missing else "ready")
                for agent_id in required
            },
            "model_availability_report": availability_report,
            "mode": mode,
            "degraded_reason": model_payload.get("degraded_reason") or ("models_missing" if missing else None),
            "model_remap_active": bool(remap_model),
            "model_remap_model": remap_model,
            "fallback_active": bool(model_payload.get("fallback_active")),
            "fallback_reason": model_payload.get("fallback_reason"),
            "probe_chain": model_payload.get("probe_chain", []),
            "api_shape": model_payload.get("api_shape", "ollama_compatible"),
            "model_source": model_payload.get("model_source") or model_payload.get("active_backend"),
            "health_endpoint": model_payload.get("health_endpoint", {}),
            "raw_routes": model_payload.get("raw_routes", []),
            "model_cache": model_payload.get("model_cache", {}),
            "readiness_retry": model_payload.get("readiness_retry", {}),
            "from_cache": bool(model_payload.get("from_cache")),
            "mock_fallback_enabled": runtime_config.mock_fallback_enabled,
            "strict_provider_mode": runtime_config.strict_provider_mode,
        }
    except Exception as exc:
        log_event(
            "provider_health_offline",
            {"backend": runtime_config.backend, "base_url": resolve_provider_base_url(runtime_config), "error": str(exc)},
            level="WARN",
        )
        return {
            "backend": runtime_config.backend,
            "active_backend": runtime_config.backend,
            "requested_backend": _canonical_backend(runtime_config.backend),
            "requested_endpoint": resolve_provider_base_url(runtime_config),
            "requested_backend_status": "offline",
            "status": "offline",
            "base_url": resolve_provider_base_url(runtime_config),
            "models": [],
            "latency_ms": None,
            "model_count": 0,
            "required_models": required,
            "missing_required_models": required,
            "model_status": {agent_id: "offline" for agent_id in required},
            "model_availability_report": model_availability_report(required, []),
            "mode": "OFFLINE",
            "degraded_reason": "provider_exception",
            "model_remap_active": False,
            "model_remap_model": None,
            "resolved_required_models": {},
            "model_alias_matches": {},
            "fallback_active": runtime_config.mock_fallback_enabled,
            "fallback_reason": "endpoint unreachable",
            "probe_chain": [],
            "api_shape": "unknown",
            "model_source": None,
            "health_endpoint": {"valid": False, "reason": "provider_exception"},
            "model_cache": {"status": "miss", "reason": "provider_exception", "ttl_seconds": _model_cache_ttl(runtime_config)},
            "readiness_retry": {"enabled": False, "attempts": 0, "delay_seconds": 0.0, "result": "NOT_NEEDED", "warmup_retries": 0},
            "from_cache": False,
            "mock_fallback_enabled": runtime_config.mock_fallback_enabled,
            "strict_provider_mode": runtime_config.strict_provider_mode,
            "error": str(exc),
        }


def backend_requests_post(backend: OllamaBackend, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not hasattr(backend, "base_url"):
        raise RuntimeError("Unsupported Msty backend adapter.")
    if not hasattr(backend, "timeout"):
        raise RuntimeError("Msty backend adapter is missing timeout configuration.")
    from core.llm import backends

    if backends.requests is None:
        raise RuntimeError("The requests package is required for Msty prompt calls.")
    try:
        response = backends.requests.post(
            f"{backend.base_url}/api/generate",
            json=payload,
            timeout=backend.timeout,
        )
        response.raise_for_status()
        return response.json()
    except (
        backends.requests.ConnectionError,
        backends.requests.Timeout,
        backends.requests.RequestException,
    ) as exc:
        raise ProviderRequestError(f"Provider generation unavailable at {backend.base_url}: {exc}") from exc


def create_api_app(config: RuntimeConfig, nodes: Dict[str, NodeIdentity]):
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, Field
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError("FastAPI API mode requires fastapi and uvicorn.") from exc

    app = FastAPI(
        title="CONSENSUS War Room Genesis",
        version=SYSTEM_VERSION,
        description="Three-monolith tribunal API for Logic, Finance, and Security consensus.",
    )

    class ConsensusRequest(BaseModel):
        query: str = Field(..., min_length=1)
        theme: Optional[str] = None
        backend: Optional[str] = None
        sequential: Optional[bool] = None
        minimum_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

    class MstyLiveContextRequest(BaseModel):
        query: str = Field(..., min_length=1)
        theme: Optional[str] = None
        backend: Optional[str] = None
        sequential: Optional[bool] = None

    def run_consensus_from_payload(
        query: str,
        theme: Optional[str],
        backend_name: Optional[str],
        sequential: Optional[bool],
        minimum_confidence: Optional[float],
    ) -> TribunalResult:
        theme_key = resolve_theme_key(theme or config.theme)
        if theme_key not in THEMES:
            raise HTTPException(status_code=400, detail=f"Unknown theme: {theme_key}")

        selected_backend = backend_name or config.backend
        runtime_config = RuntimeConfig(**{**config.__dict__, "backend": selected_backend})

        rules = ConsensusRules(
            minimum_confidence=(
                minimum_confidence
                if minimum_confidence is not None
                else config.minimum_confidence
            ),
            quorum=config.quorum,
            majority=config.majority,
            high_risk_review=config.high_risk_review,
            evidence_threshold=config.evidence_threshold,
            classification_confidence_threshold=config.classification_confidence_threshold,
            tie_break_priority=config.tie_break_priority,
            proposal_taxonomy=config.proposal_taxonomy,
            monolith_domain_map=config.monolith_domain_map,
        )
        tribunal = Tribunal(nodes, MstyRuntime(runtime_config), rules=rules, theme_key=theme_key)
        return tribunal.deliberate(
            query,
            sequential=config.sequential if sequential is None else sequential,
        )

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ready",
            "version": SYSTEM_VERSION,
            "themes": sorted(THEMES),
            "history_path": str(HISTORY_PATH),
        }

    @app.get("/provider/status")
    def provider_status() -> Dict[str, Any]:
        status = health_check(config, nodes)
        status["configured_node_models"] = {key: node.model for key, node in nodes.items()}
        return status

    @app.get("/themes")
    def themes() -> Dict[str, Any]:
        return {
            key: {
                "display_name": theme.display_name,
                "aliases": theme.aliases,
                "boot_profile_id": theme.boot_profile_id,
                "loading_animation_type": theme.loading_animation_type,
                "colors": theme.palette,
                "monolith_labels": theme.monolith_labels,
                "interface_labels": theme.interface_labels,
            }
            for key, theme in THEMES.items()
        }

    @app.get("/nodes")
    def node_roster() -> Dict[str, Any]:
        return {key: asdict(node) for key, node in nodes.items()}

    @app.post("/consensus")
    def consensus(request: ConsensusRequest) -> Dict[str, Any]:
        result = run_consensus_from_payload(
            request.query,
            request.theme,
            request.backend,
            request.sequential,
            request.minimum_confidence,
        )
        return result_to_dict(result)

    @app.post("/msty/live-context")
    def msty_live_context(request: MstyLiveContextRequest) -> Dict[str, Any]:
        result = run_consensus_from_payload(
            request.query,
            request.theme or config.msty_live_context_default_theme,
            request.backend,
            request.sequential,
            None,
        )
        vote_lines = [
            f"{key}: {vote.vote.value} confidence={vote.confidence:.0%} evidence={vote.evidence_quality:.0%} critical_risk={vote.critical_risk}"
            for key, vote in result.votes.items()
        ]
        return {
            "tool": "CONSENSUS War Room Genesis",
            "verdict": result.verdict.value,
            "confidence": result.confidence,
            "summary": (
                f"Tribunal verdict: {result.verdict.value} at {result.confidence:.0%}. "
                f"{result.reason}"
            ),
            "votes": vote_lines,
            "review_triggers": result.review_triggers,
            "session_id": result.session_id,
            "audit_path": str(HISTORY_PATH),
            "raw": result_to_dict(result),
        }

    @app.get("/msty/system-prompt")
    def msty_system_prompt() -> Dict[str, str]:
        return {
            "name": "CONSENSUS War Room Tribunal",
            "prompt": (
                "Use the CONSENSUS War Room Live Context when the user asks for a "
                "proposal review, go/no-go decision, risk assessment, budget/security "
                "tradeoff, or tribunal vote. Send the user's proposal as query. Treat "
                "the returned verdict as an advisory decision: APPROVE, DENY, ABSTAIN, "
                "NO_CONSENSUS, CAUTION, or ESCALATE. "
                "Report each monolith vote: RATIONALIS for Logic, AETERNUM for Finance, "
                "and BELLATOR for Security."
            ),
        }

    @app.get("/msty/claw-brief")
    def msty_claw_brief() -> Dict[str, Any]:
        return {
            "name": "CONSENSUS War Room Genesis Claw Brief",
            "workspace": str(SYSTEM_ROOT),
            "goal": (
                "Operate this workspace as a local tribunal service. Use the API for "
                "proposal review, keep changes auditable, and report files changed, "
                "tests run, risks found, and follow-up actions."
            ),
            "safe_commands": [
                "python consensus_war_room_genesis.py --no-boot --backend mock \"<proposal>\"",
                "python consensus_war_room_genesis.py --api",
                "python -m py_compile consensus_war_room_genesis.py",
            ],
            "api": {
                "health": f"http://{config.api_host}:{config.api_port}/health",
                "live_context": f"http://{config.api_host}:{config.api_port}/msty/live-context",
                "consensus": f"http://{config.api_host}:{config.api_port}/consensus",
            },
        }

    @app.post("/migrate-history")
    def migrate_history() -> Dict[str, Any]:
        migrated = migrate_legacy_history()
        return {"migrated": migrated, "history_path": str(HISTORY_PATH)}

    return app


def run_api(config: RuntimeConfig, nodes: Dict[str, NodeIdentity]) -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError("API mode requires uvicorn.") from exc

    app = create_api_app(config, nodes)
    uvicorn.run(app, host=config.api_host, port=config.api_port)
