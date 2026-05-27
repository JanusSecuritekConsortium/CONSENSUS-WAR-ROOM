from __future__ import annotations

import argparse
import json
import random
from dataclasses import replace
from pathlib import Path

from config.agents import AGENT_PROFILES
from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import apply_cli_overrides, load_runtime_config, runtime_config_to_dict, write_default_config
from core.active_compile import compile_active_sources, print_compile_report
from core.health import print_health_report, run_health_check
from core.history import migrate_legacy_history
from core.logging import log_event
from core.paths import CONFIG_PATH, HISTORY_PATH
from core.tribunal import Tribunal
from core.voting.rules import ConsensusRules
from integrations.msty.runtime import MstyRuntime
from integrations.msty.api import run_api
from ui.rendering import render_boot, render_node_roster, render_result
from ui.animations.bios_boot import render_bios_boot_console
from ui.animations.boot import export_legacy_visual_reference, export_theme_preview, render_theme_preview
from ui.animations.loading import render_loading_console
from ui.themes.catalog import (
    THEME_ALIASES,
    THEMES,
    get_gui_theme_key,
    get_gui_theme_options,
    list_themes,
    resolve_theme_key,
)


def resolve_selected_theme(cli_theme: str | None, seed: int | None = None) -> str:
    if cli_theme:
        return resolve_theme_key(cli_theme)
    rng = random.Random(seed)
    return rng.choice(sorted(THEMES))


def resolve_selected_gui_theme(cli_theme: str | None, seed: int | None = None) -> str:
    if cli_theme:
        return get_gui_theme_key(cli_theme)
    rng = random.Random(seed)
    return rng.choice([theme.key for theme in get_gui_theme_options()])


def resolve_gui_window_mode(fullscreen: bool = False, maximized: bool = False, windowed: bool = False) -> str:
    if fullscreen:
        return "fullscreen"
    if windowed:
        return "windowed"
    return "maximized"


MODEL_CONFIG_AGENT_IDS = (ARBITER, *TRIBUNAL_AGENT_IDS)


def _normalize_model_agent(agent_id: str) -> str:
    normalized = agent_id.strip().upper()
    if normalized not in MODEL_CONFIG_AGENT_IDS:
        allowed = ", ".join(MODEL_CONFIG_AGENT_IDS)
        raise SystemExit(f"Unknown monolith: {agent_id}. Allowed: {allowed}")
    return normalized


def _effective_model_config(config) -> dict[str, str]:
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    overrides = config.agent_model_overrides or {}
    models = {ARBITER: overrides.get(ARBITER, AGENT_PROFILES[ARBITER].model_preference)}
    for agent_id in TRIBUNAL_AGENT_IDS:
        models[agent_id] = overrides.get(agent_id, nodes[agent_id].model)
    return models


def _write_model_override(config_path: Path, agent_id: str, model_name: str) -> None:
    config_for_update = load_runtime_config(config_path)
    data = runtime_config_to_dict(config_for_update)
    agent_model_overrides = dict(data.get("agent_model_overrides") or {})
    agent_model_overrides[agent_id] = model_name
    data["agent_model_overrides"] = agent_model_overrides

    if agent_id in DEFAULT_NODES:
        node_overrides = dict(data.get("node_overrides") or {})
        patch = dict(node_overrides.get(agent_id, {}))
        patch["model"] = model_name
        node_overrides[agent_id] = patch
        data["node_overrides"] = node_overrides

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _warn_if_model_unavailable(config, model_name: str) -> None:
    from integrations.msty.api import list_models

    payload = list_models(replace(config, refresh_model_cache=True))
    status = str(payload.get("status", "offline")).lower()
    if status == "offline":
        print("WARNING: provider offline; unable to verify model availability.")
        return
    available = set(payload.get("models", []) or [])
    if model_name not in available:
        print(f"WARNING: model is not currently available from provider: {model_name}")
        print(f"ACTIVE BACKEND: {payload.get('active_backend') or payload.get('backend')}")
        print(f"ENDPOINT: {payload.get('base_url') or '--'}")


def resolve_runtime_provider_status(config, nodes) -> dict:
    from integrations.msty.api import health_check

    return health_check(config, nodes)


def _print_provider_resolution(payload: dict, verbose: bool = False) -> None:
    requested_backend = payload.get("requested_backend") or payload.get("backend") or "--"
    resolved_backend = payload.get("active_backend") or payload.get("backend") or "--"
    requested_endpoint = payload.get("requested_endpoint") or payload.get("base_url") or "--"
    resolved_endpoint = payload.get("base_url") or "--"
    fallback_active = bool(payload.get("fallback_active"))

    print(f"REQUESTED BACKEND: {requested_backend}")
    print(f"REQUESTED ENDPOINT: {requested_endpoint}")
    print(f"REQUESTED BACKEND STATUS: {str(payload.get('requested_backend_status', payload.get('status', 'unknown'))).upper()}")
    print(f"FALLBACK ACTIVATED: {'YES' if fallback_active else 'NO'}")
    if fallback_active:
        print(f"FALLBACK REASON: {payload.get('fallback_reason') or 'endpoint unreachable'}")
    print(f"RESOLVED BACKEND: {resolved_backend}")
    print(f"RESOLVED ENDPOINT: {resolved_endpoint}")
    if not verbose:
        return
    print("RESOLUTION CHAIN:")
    for index, probe in enumerate(payload.get("probe_chain", []) or [], start=1):
        print(
            f"{index}. {probe.get('source')} | {probe.get('backend')} | {probe.get('base_url')} | "
            f"{str(probe.get('status', 'unknown')).upper()} | {probe.get('latency_ms', '--')} ms"
        )
    print(f"API SHAPE: {payload.get('api_shape') or '--'}")
    print(f"MODEL SOURCE: {payload.get('model_source') or '--'}")
    retry = payload.get("readiness_retry", {}) or {}
    if retry:
        print(f"READINESS RETRY: {'ENABLED' if retry.get('enabled') else 'DISABLED'}")
        print(f"READINESS ATTEMPTS: {retry.get('attempts', '--')}")
        print(f"READINESS RESULT: {retry.get('result', 'NOT_NEEDED')}")
        if retry.get("warmup_retries"):
            print(f"WARMUP RETRIES: {retry.get('warmup_retries')}")
    cache = payload.get("model_cache", {}) or {}
    if cache:
        status = str(cache.get("status", "unknown")).upper()
        print(f"MODEL CACHE: {status}")
        if cache.get("age_seconds") is not None:
            print(f"CACHE AGE: {cache.get('age_seconds')}s")
        if cache.get("ttl_seconds") is not None:
            print(f"CACHE TTL: {cache.get('ttl_seconds')}s")
        if cache.get("latency_ms_original") is not None:
            print(f"ORIGINAL ENUMERATION LATENCY: {cache.get('latency_ms_original')} ms")
        if cache.get("current_check_latency_ms") is not None:
            print(f"CURRENT CHECK LATENCY: {cache.get('current_check_latency_ms')} ms")
        if cache.get("reason"):
            print(f"CACHE REASON: {cache.get('reason')}")
    alias_matches = payload.get("model_alias_matches", {}) or {}
    if alias_matches:
        print("MODEL ALIAS MATCHES:")
        for agent_id, match in alias_matches.items():
            print(
                f"- {agent_id}: {match.get('configured')} -> {match.get('resolved')} "
                f"({match.get('match_type')})"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="CONSENSUS War Room Genesis")
    parser.add_argument("query", nargs="*", help="Proposal to submit to the tribunal")
    parser.add_argument("--config", type=Path, default=None, help="Path to Genesis config JSON")
    parser.add_argument("--write-default-config", action="store_true", help="Create default config and exit")
    parser.add_argument("--migrate-history", action="store_true", help="Import legacy history into Genesis audit log")
    parser.add_argument("--health", action="store_true", help="Run module health checks and exit")
    parser.add_argument("--compile-active", action="store_true", help="Compile active modular source files and exit")
    parser.add_argument("--boot-demo", action="store_true", help="Run animated BIOS-style boot demo and exit")
    parser.add_argument("--loading-demo", action="store_true", help="Run selected theme loading animation demo and exit")
    parser.add_argument("--gui", action="store_true", help="Run the Flet War Room GUI")
    parser.add_argument("--provider-status", action="store_true", help="Show Msty/Ollama provider status and exit")
    parser.add_argument("--provider-diagnose", action="store_true", help="Probe known Msty/Ollama endpoints and API shapes")
    parser.add_argument("--list-models", action="store_true", help="Show available provider models and exit")
    parser.add_argument("--check-models", action="store_true", help="Check required monolith models and exit")
    parser.add_argument("--verbose", action="store_true", help="Show detailed provider resolution diagnostics for health/provider commands")
    parser.add_argument("--memory-status", action="store_true", help="Show persistent memory status and exit")
    parser.add_argument("--session-summary", action="store_true", help="Show recent session memory summary and exit")
    parser.add_argument("--export-session", action="store_true", help="Export current session memory snapshot to _ARBITER/exports")
    parser.add_argument("--search-decisions", default=None, help="Search prior decisions using keyword overlap")
    parser.add_argument(
        "--compact-header",
        action="store_true",
        default=True,
        help="Use the contained compact GUI header logo",
    )
    window_group = parser.add_mutually_exclusive_group()
    window_group.add_argument("--fullscreen", action="store_true", help="Launch GUI in fullscreen mode")
    window_group.add_argument("--maximized", action="store_true", help="Launch GUI maximized (default)")
    window_group.add_argument("--windowed", action="store_true", help="Launch GUI in normal windowed mode")
    parser.add_argument("--api", action="store_true", help="Run the FastAPI service")
    parser.add_argument("--theme", default=None, choices=sorted(set(THEMES.keys()) | set(THEME_ALIASES.keys())))
    parser.add_argument("--speed", default="random", choices=["fast", "normal", "slow", "random"], help="Animation speed for --boot-demo and --loading-demo")
    parser.add_argument("--seed", type=int, default=None, help="Seed randomized boot/loading timing")
    parser.add_argument("--backend", default=None, choices=["mock", "ollama", "msty-local", "msty-claw", "msty-llama-cpp"])
    parser.add_argument("--msty-base-url", default=None, help="Override Msty/Ollama-compatible provider endpoint")
    parser.add_argument("--ollama-base-url", default=None, help="Override Ollama-compatible provider endpoint")
    parser.add_argument("--msty-llama-cpp-base-url", default=None, help="Override lower-level Msty LLaMA.cpp endpoint")
    parser.add_argument("--no-mock-fallback", action="store_true", help="Disable mock fallback for missing/offline provider models")
    parser.add_argument("--strict-provider-mode", action="store_true", help="Fail instead of falling back when provider/models are unavailable")
    parser.add_argument("--use-available-model-fallback", action="store_true", help="Temporarily remap missing required models to the first available provider model")
    parser.add_argument("--refresh-model-cache", action="store_true", help="Bypass and refresh the short-lived provider model cache")
    parser.add_argument("--set-all-models", default=None, help="Persistently set ARBITER and all tribunal monolith models in the runtime config")
    parser.add_argument("--set-model", nargs=2, metavar=("MONOLITH", "MODEL"), help="Persistently set one monolith model in the runtime config")
    parser.add_argument("--show-model-config", action="store_true", help="Show configured ARBITER and tribunal monolith models")
    parser.add_argument("--sequential", action="store_true", help="Share prior votes as context")
    parser.add_argument("--no-boot", action="store_true", help="Skip boot screen")
    parser.add_argument("--list-themes", action="store_true", help="Show available themes")
    parser.add_argument("--preview-theme", default=None, choices=sorted(set(THEMES.keys()) | set(THEME_ALIASES.keys())), help="Show a theme boot/loading preview and exit")
    parser.add_argument("--export-preview", action="store_true", help="Write --preview-theme output to _ARBITER/theme_previews")
    parser.add_argument("--export-legacy-visuals", action="store_true", help="Export recovered legacy logos and boot sample")
    parser.add_argument("--minimum-confidence", type=float, default=None)
    parser.add_argument("--quorum", type=int, default=None)
    parser.add_argument("--majority", type=int, default=None)
    parser.add_argument("--no-high-risk-review", action="store_true")
    parser.add_argument("--api-host", default=None)
    parser.add_argument("--api-port", type=int, default=None)
    args = parser.parse_args()
    log_event("system_command", {"command": "main", "args": vars(args)})

    if args.list_themes:
        list_themes()
        return
    if args.compile_active:
        result = compile_active_sources()
        print_compile_report(result)
        if not result.ok:
            raise SystemExit(1)
        return
    if args.loading_demo:
        render_loading_console(theme_id=resolve_selected_theme(args.theme, args.seed), speed=args.speed, seed=args.seed)
        return
    if args.export_legacy_visuals:
        path = export_legacy_visual_reference()
        print(f"Legacy visual reference exported to: {path}")
        return
    if args.preview_theme:
        theme_key = resolve_theme_key(args.preview_theme)
        if theme_key not in THEMES:
            raise SystemExit(f"Unknown theme: {args.preview_theme}")
        if args.export_preview:
            path = export_theme_preview(THEMES[theme_key])
            print(f"Theme preview exported to: {path}")
        else:
            render_theme_preview(THEMES[theme_key])
        return

    config_path = args.config or CONFIG_PATH
    if args.health:
        health_config = apply_cli_overrides(load_runtime_config(config_path), args)
        report = run_health_check(config_path, config_override=health_config)
        print_health_report(report, verbose=args.verbose)
        if report["status"] == "fail":
            raise SystemExit(1)
        return
    if args.write_default_config:
        write_default_config(config_path)
        print(f"Default config available at: {config_path}")
        return

    if args.set_all_models:
        config_for_update = load_runtime_config(config_path)
        model_name = args.set_all_models.strip()
        if not model_name:
            raise SystemExit("--set-all-models requires a model name")
        data = runtime_config_to_dict(config_for_update)
        node_overrides = dict(data.get("node_overrides") or {})
        for agent_id in DEFAULT_NODES:
            patch = dict(node_overrides.get(agent_id, {}))
            patch["model"] = model_name
            node_overrides[agent_id] = patch
        agent_model_overrides = dict(data.get("agent_model_overrides") or {})
        for agent_id in [ARBITER, *DEFAULT_NODES.keys()]:
            agent_model_overrides[agent_id] = model_name
        data["node_overrides"] = node_overrides
        data["agent_model_overrides"] = agent_model_overrides
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Configured ARBITER and tribunal monolith models as: {model_name}")
        print(f"Updated config: {config_path}")
        return

    if args.set_model:
        agent_id = _normalize_model_agent(args.set_model[0])
        model_name = args.set_model[1].strip()
        if not model_name:
            raise SystemExit("--set-model requires a model name")
        _write_model_override(config_path, agent_id, model_name)
        print(f"Configured {agent_id} model as: {model_name}")
        print(f"Updated config: {config_path}")
        verification_config = apply_cli_overrides(load_runtime_config(config_path), args)
        _warn_if_model_unavailable(verification_config, model_name)
        return

    config = apply_cli_overrides(load_runtime_config(config_path), args)
    if args.memory_status:
        from core.memory.session import memory_status

        status = memory_status()
        print("SESSION MEMORY:", status["session_memory"])
        print("SESSION COUNT:", status["session_count"])
        print("SESSION MEMORY PATH:", status["session_memory_path"])
        print("CONTEXT INDEX PATH:", status["context_index_path"])
        print("CONTEXT INDEX EXISTS:", status["context_index_exists"])
        return
    if args.session_summary:
        from core.memory.session import session_summary

        print(session_summary())
        return
    if args.export_session:
        import shutil
        from datetime import datetime
        from core.paths import EXPORT_DIR, SESSION_MEMORY_PATH

        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        target = EXPORT_DIR / f"session_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if SESSION_MEMORY_PATH.exists():
            shutil.copy2(SESSION_MEMORY_PATH, target)
        else:
            target.write_text('{"version": 1, "sessions": []}\n', encoding="utf-8")
        print(f"Session memory exported to: {target}")
        return
    if args.search_decisions is not None:
        from core.memory.retrieval import search_decisions

        results = search_decisions(args.search_decisions)
        print(f"SEARCH RESULTS: {len(results)}")
        for item in results:
            print(f"- {item.get('session_id', '--')} | {item.get('verdict', '--')} | {item.get('proposal', '')[:120]}")
        return
    if args.show_model_config:
        for agent_id, model_name in _effective_model_config(config).items():
            print(f"{agent_id}: {model_name}")
        return
    config.theme = resolve_selected_gui_theme(args.theme, args.seed) if args.gui else resolve_selected_theme(args.theme, args.seed)
    if config.theme not in THEMES:
        raise SystemExit(f"Unknown configured theme: {config.theme}")
    if config.backend not in {"mock", "ollama", "msty-local", "msty-claw", "msty-llama-cpp"}:
        raise SystemExit(f"Unknown configured backend: {config.backend}")
    if not 0.0 <= config.minimum_confidence <= 1.0:
        raise SystemExit("minimum_confidence must be between 0.0 and 1.0")
    if not 0.0 <= config.evidence_threshold <= 1.0:
        raise SystemExit("evidence_threshold must be between 0.0 and 1.0")
    if not 0.0 <= config.classification_confidence_threshold <= 1.0:
        raise SystemExit("classification_confidence_threshold must be between 0.0 and 1.0")
    if config.quorum < 1 or config.majority < 1:
        raise SystemExit("quorum and majority must be positive integers")

    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)

    if args.provider_status or args.provider_diagnose or args.list_models or args.check_models:
        from integrations.msty.api import health_check, list_models, provider_diagnostics

        if args.provider_diagnose:
            diagnostics = provider_diagnostics(config)
            print("PROVIDER DIAGNOSTICS")
            print("Priority:")
            for index, candidate in enumerate(diagnostics["candidate_priority"], start=1):
                print(
                    f"{index}. {candidate['source']} | {candidate['backend']} | {candidate['base_url']}"
                )
            print("Endpoints:")
            for endpoint in diagnostics["endpoints"]:
                status = "REACHABLE" if endpoint["reachable"] else "OFFLINE"
                shapes = ", ".join(endpoint["api_shapes"]) or "none"
                print(f"- {endpoint['name']}: {status}")
                print(f"  BACKEND: {endpoint['backend']}")
                print(f"  ENDPOINT: {endpoint['base_url']}")
                print(f"  ROLE: {endpoint['role']}")
                print(f"  MODEL INFERENCE: {endpoint.get('model_inference', '--')}")
                print(f"  CLASSIFICATION: {endpoint.get('service_classification', '--')}")
                print(f"  API SHAPES: {shapes}")
                print(f"  MODEL COUNT: {endpoint['model_count']}")
                if args.verbose:
                    print("  ROUTES:")
                    for route in endpoint.get("raw_routes", []) or []:
                        models = ", ".join(route.get("models", []) or [])
                        rejection = route.get("rejection_reason") or "--"
                        print(
                            f"  - {route.get('path')}: {route.get('status_code') or '--'} | "
                            f"{route.get('content_type') or '--'} | {route.get('detected_schema') or '--'} | "
                            f"models=[{models}] | reason={rejection}"
                        )
            return

        if args.list_models:
            payload = list_models(config)
            status = str(payload.get("status", "ready")).upper()
            model_count = payload.get("model_count", len(payload.get("models", []) or []))
            print(f"PROVIDER STATUS: {status}")
            _print_provider_resolution(payload, verbose=args.verbose)
            active_backend = payload.get("active_backend") or payload.get("backend")
            print(f"ACTIVE BACKEND: {active_backend}")
            print(f"BACKEND: {active_backend}")
            print(f"PROVIDER: {active_backend}")
            print(f"ENDPOINT: {payload.get('base_url') or '--'}")
            print(f"LATENCY: {payload.get('latency_ms', '--')} ms")
            print(f"MODEL COUNT: {model_count}")
            if status == "OFFLINE":
                print("No models available because provider is offline.")
                return
            for model in payload.get("models", []):
                print(f"- {model}")
            return

        provider_config = replace(config, refresh_model_cache=True) if args.check_models else config
        status = resolve_runtime_provider_status(provider_config, nodes)
        print(f"PROVIDER STATUS: {str(status.get('status', 'unknown')).upper()}")
        _print_provider_resolution(status, verbose=args.verbose)
        active_backend = status.get("active_backend") or status.get("backend")
        print(f"ACTIVE BACKEND: {active_backend}")
        print(f"BACKEND: {active_backend}")
        print(f"ENDPOINT: {status.get('base_url') or '--'}")
        print(f"LATENCY: {status.get('latency_ms', '--')} ms")
        print(f"MODEL COUNT: {status.get('model_count', 0)}")
        if status.get("degraded_reason"):
            print(f"DEGRADED REASON: {status.get('degraded_reason')}")
        if str(status.get("status", "")).lower() == "offline":
            print("No models available because provider is offline.")
        print(f"MOCK FALLBACK: {'ENABLED' if status.get('mock_fallback_enabled') else 'DISABLED'}")
        print(f"STRICT MODE: {'ENABLED' if status.get('strict_provider_mode') else 'DISABLED'}")
        if status.get("model_remap_active"):
            print(f"MODEL REMAP ACTIVE: {status.get('model_remap_model')}")
        missing = status.get("missing_required_models", {})
        if missing:
            print("MISSING REQUIRED MODELS:")
            for agent_id, model in missing.items():
                print(f"- {agent_id}: {model}")
        else:
            print("MISSING REQUIRED MODELS: none")
        if args.check_models and missing and config.strict_provider_mode:
            raise SystemExit(1)
        return

    if args.boot_demo:
        provider_status = resolve_runtime_provider_status(config, nodes)
        render_bios_boot_console(
            theme_id=config.theme,
            speed=args.speed,
            seed=args.seed,
            provider_status=provider_status,
        )
        return

    if args.migrate_history:
        migrated = migrate_legacy_history()
        print(f"Migrated {migrated} legacy records into: {HISTORY_PATH}")
        if not args.query and not args.api:
            return

    if args.api:
        run_api(config, nodes)
        return

    if args.gui:
        provider_status = resolve_runtime_provider_status(config, nodes)
        render_bios_boot_console(theme_id=config.theme, speed=args.speed, seed=args.seed, provider_status=provider_status)
        from ui.flet_app import run_flet_gui

        run_flet_gui(
            config.theme,
            config,
            nodes,
            compact_header=args.compact_header,
            window_mode=resolve_gui_window_mode(args.fullscreen, args.maximized, args.windowed),
        )
        return

    query = " ".join(args.query).strip()
    if not query:
        query = input("Proposal: ").strip()
    if not query:
        raise SystemExit("No proposal provided.")

    theme = THEMES[config.theme]
    if not args.no_boot:
        provider_status = resolve_runtime_provider_status(config, nodes)
        render_boot(theme, seed=args.seed, provider_status=provider_status)
    render_node_roster(theme, nodes)

    runtime = MstyRuntime(config)
    rules = ConsensusRules(
        minimum_confidence=config.minimum_confidence,
        quorum=config.quorum,
        majority=config.majority,
        high_risk_review=config.high_risk_review,
        evidence_threshold=config.evidence_threshold,
        classification_confidence_threshold=config.classification_confidence_threshold,
        tie_break_priority=config.tie_break_priority,
        proposal_taxonomy=config.proposal_taxonomy,
        monolith_domain_map=config.monolith_domain_map,
    )
    tribunal = Tribunal(nodes, runtime, rules=rules, theme_key=theme.key)
    result = tribunal.deliberate(query, sequential=config.sequential)
    render_result(result, theme)
    print(f"Audit record written to: {HISTORY_PATH}")
