from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config.names import CANONICAL_AGENT_IDS, TRIBUNAL_AGENT_IDS
from config.runtime import RuntimeConfig, load_runtime_config
from core.logging import log_error, log_event
from core.memory.store import MemoryStore
from core.models import NodeIdentity, VoteValue
from core.paths import ARBITER_DIR, CONFIG_PATH, EXPORT_DIR, LOG_DIR, MEMORY_PATH, SYSTEM_ROOT
from core.voting.parser import parse_vote
from monoliths.registry import DEFAULT_NODES


REQUIRED_FOLDERS: List[Path] = [
    ARBITER_DIR,
    ARBITER_DIR / "memory",
    ARBITER_DIR / "logs",
    ARBITER_DIR / "exports",
    ARBITER_DIR / "tts_audio",
    ARBITER_DIR / "tmp_votes",
    EXPORT_DIR,
    LOG_DIR,
    SYSTEM_ROOT / "core",
    SYSTEM_ROOT / "core" / "voting",
    SYSTEM_ROOT / "core" / "memory",
    SYSTEM_ROOT / "core" / "llm",
    SYSTEM_ROOT / "core" / "knowledge",
    SYSTEM_ROOT / "config",
    SYSTEM_ROOT / "integrations",
    SYSTEM_ROOT / "integrations" / "msty",
    SYSTEM_ROOT / "integrations" / "ollama",
    SYSTEM_ROOT / "monoliths",
    SYSTEM_ROOT / "monoliths" / "rationalis",
    SYSTEM_ROOT / "monoliths" / "aeternum",
    SYSTEM_ROOT / "monoliths" / "bellator",
    SYSTEM_ROOT / "ui",
    SYSTEM_ROOT / "ui" / "themes",
    SYSTEM_ROOT / "ui" / "components",
    SYSTEM_ROOT / "ui" / "animations",
    SYSTEM_ROOT / "ui" / "assets",
    SYSTEM_ROOT / "static",
]


def ensure_required_folders() -> None:
    for folder in REQUIRED_FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)


def run_health_check(config_path: Path = CONFIG_PATH, config_override: RuntimeConfig | None = None) -> Dict[str, Any]:
    checks: Dict[str, Dict[str, Any]] = {}
    log_event("system_command", {"command": "health_check", "config_path": str(config_path)})

    def pass_check(name: str, detail: Dict[str, Any]) -> None:
        checks[name] = {**detail, "status": "pass"}

    def fail_check(name: str, exc: Exception) -> None:
        checks[name] = {
            "status": "fail",
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }
        log_error("health_check_error", exc, {"check": name})

    def degraded_check(name: str, detail: Dict[str, Any]) -> None:
        checks[name] = {**detail, "status": "degraded"}

    try:
        config = config_override or load_runtime_config(config_path)
        if not isinstance(config, RuntimeConfig):
            raise RuntimeError("Config loader did not return RuntimeConfig.")
        pass_check("config_load", {"theme": config.theme, "backend": config.backend})
    except Exception as exc:
        fail_check("config_load", exc)

    try:
        from core.themes import THEMES, validate_theme_catalog

        validate_theme_catalog()
        pass_check("theme_catalog_load", {"themes": sorted(THEMES)})
    except Exception as exc:
        fail_check("theme_catalog_load", exc)

    try:
        ensure_required_folders()
        missing = [str(folder) for folder in REQUIRED_FOLDERS if not folder.exists() or not folder.is_dir()]
        if missing:
            raise RuntimeError(f"Missing folders: {', '.join(missing)}")
        pass_check("required_folders", {"count": len(REQUIRED_FOLDERS)})
    except Exception as exc:
        fail_check("required_folders", exc)

    try:
        from core.active_compile import compile_active_sources

        compile_result = compile_active_sources()
        if not compile_result.ok:
            raise RuntimeError("; ".join(compile_result.failures[:5]))
        pass_check("active_source_compile", {"files": len(compile_result.compiled)})
    except Exception as exc:
        fail_check("active_source_compile", exc)

    try:
        store = MemoryStore()
        memory = store.load()
        memory.setdefault("_health", {})["last_check"] = datetime.now().isoformat()
        store.save(memory)
        reloaded = store.load()
        if "_health" not in reloaded:
            raise RuntimeError("Memory health marker was not persisted.")
        pass_check("memory_store_read_write", {"path": str(MEMORY_PATH)})
    except Exception as exc:
        fail_check("memory_store_read_write", exc)

    try:
        node = NodeIdentity(
            role="Health",
            codename="RATIONALIS",
            core_name="Health Core",
            monolith_name="RATIONALIS",
            symbol="H",
            model="mock",
            temperature=0.0,
            mission="verify parser",
            prompt="health parser",
        )
        vote = parse_vote(
            "VOTE: APPROVE\nCONFIDENCE: 0.88\nREASONING: parser ok\nRISKS: none\nCONDITIONS: none",
            node,
            0.0,
            "mock",
        )
        if vote.vote != VoteValue.APPROVE or vote.confidence != 0.88:
            raise RuntimeError("Voting parser returned unexpected output.")
        pass_check("voting_parser", {"vote": vote.vote.value, "confidence": vote.confidence})
    except Exception as exc:
        fail_check("voting_parser", exc)

    try:
        from integrations.msty.api import health_check, list_models, send_prompt

        if not callable(health_check) or not callable(list_models) or not callable(send_prompt):
            raise RuntimeError("Msty API functions are not callable.")
        pass_check("msty_api_import", {"functions": ["list_models", "send_prompt", "health_check"]})
    except Exception as exc:
        fail_check("msty_api_import", exc)

    try:
        from integrations.msty.runtime import MstyRuntime

        runtime_config = config if "config" in locals() else RuntimeConfig()
        runtime_status = MstyRuntime(runtime_config).health_check()
        if runtime_status["status"] == "ready":
            pass_check("msty_runtime_health", runtime_status)
        else:
            degraded_check("msty_runtime_health", runtime_status)
    except Exception as exc:
        fail_check("msty_runtime_health", exc)

    try:
        registry_ids = set(DEFAULT_NODES)
        missing_nodes = set(TRIBUNAL_AGENT_IDS) - registry_ids
        if missing_nodes:
            raise RuntimeError(f"Missing monolith registry IDs: {', '.join(sorted(missing_nodes))}")
        pass_check(
            "monolith_registry",
            {
                "canonical_agent_ids": list(CANONICAL_AGENT_IDS),
                "tribunal_agents": list(TRIBUNAL_AGENT_IDS),
                "nodes": {key: asdict(value) for key, value in DEFAULT_NODES.items()},
            },
        )
    except Exception as exc:
        fail_check("monolith_registry", exc)

    if any(check["status"] == "fail" for check in checks.values()):
        status = "fail"
    elif any(check["status"] == "degraded" for check in checks.values()):
        status = "degraded"
    else:
        status = "pass"
    payload = {"status": status, "checks": checks}
    log_event("health_check", payload, level="INFO" if status == "pass" else "ERROR")
    return payload


def print_health_report(report: Dict[str, Any], verbose: bool = False) -> None:
    print(f"HEALTH: {report['status'].upper()}")
    for name, check in report["checks"].items():
        if check["status"] == "pass":
            print(f"[PASS] {name}")
        elif check["status"] == "degraded":
            print(f"[DEGRADED] {name}")
        else:
            print(f"[FAIL] {name}: {check.get('error')}")
        if verbose and name == "msty_runtime_health":
            provider = check.get("provider", {})
            print(f"  REQUESTED BACKEND: {provider.get('requested_backend') or provider.get('backend') or '--'}")
            print(f"  REQUESTED ENDPOINT: {provider.get('requested_endpoint') or provider.get('base_url') or '--'}")
            print(f"  RESOLVED BACKEND: {provider.get('active_backend') or provider.get('backend') or '--'}")
            print(f"  RESOLVED ENDPOINT: {provider.get('base_url') or '--'}")
            print(f"  FALLBACK ACTIVE: {'YES' if provider.get('fallback_active') else 'NO'}")
            print(f"  LATENCY: {provider.get('latency_ms', '--')} ms")
            print(f"  API SHAPE: {provider.get('api_shape') or '--'}")
            print(f"  MODEL SOURCE: {provider.get('model_source') or '--'}")
            print(f"  DEGRADED REASON: {provider.get('degraded_reason') or '--'}")
            retry = provider.get("readiness_retry", {}) or {}
            if retry:
                print(f"  READINESS RETRY: {'ENABLED' if retry.get('enabled') else 'DISABLED'}")
                print(f"  READINESS ATTEMPTS: {retry.get('attempts', '--')}")
                print(f"  READINESS RESULT: {retry.get('result', 'NOT_NEEDED')}")
                if retry.get("warmup_retries"):
                    print(f"  WARMUP RETRIES: {retry.get('warmup_retries')}")
            cache = provider.get("model_cache", {}) or {}
            if cache:
                print(f"  MODEL CACHE: {str(cache.get('status', 'unknown')).upper()}")
                if cache.get("age_seconds") is not None:
                    print(f"  CACHE AGE: {cache.get('age_seconds')}s")
                if cache.get("ttl_seconds") is not None:
                    print(f"  CACHE TTL: {cache.get('ttl_seconds')}s")
                if cache.get("latency_ms_original") is not None:
                    print(f"  ORIGINAL ENUMERATION LATENCY: {cache.get('latency_ms_original')} ms")
                if cache.get("current_check_latency_ms") is not None:
                    print(f"  CURRENT CHECK LATENCY: {cache.get('current_check_latency_ms')} ms")
                if cache.get("reason"):
                    print(f"  CACHE REASON: {cache.get('reason')}")
            missing = provider.get("missing_required_models", {}) or {}
            print(f"  MISSING MODELS: {len(missing)}")
            for index, probe in enumerate(provider.get("probe_chain", []) or [], start=1):
                print(
                    f"  {index}. {probe.get('source')} | {probe.get('backend')} | {probe.get('base_url')} | "
                    f"{str(probe.get('status', 'unknown')).upper()} | {probe.get('latency_ms', '--')} ms"
                )
