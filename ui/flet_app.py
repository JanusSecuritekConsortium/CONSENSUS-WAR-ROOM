from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import sys
import time
import uuid
import importlib.util
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal

import flet as ft

from assistant.aurelius_runtime import AureliusRuntime, get_aurelius_runtime
from config.names import AETERNUM, ARBITER, BELLATOR, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import RuntimeConfig
from config.version import SYSTEM_VERSION
from core.history import record_result
from core.directorate import Directorate, STARTUP_COMPONENTS, provider_observation, read_preferences, write_preferences
from core.export.cable import export_cable, export_dispatch, render_cable, retrieved_sources
from ui.directorate import add_cable_controls, build_activity, build_boot, build_dispatch_desk, build_dispatch_roll, build_dispatch_actions
from ui.deliberation import assessment_record, build_assessments
from core.decision_trace import list_recent_traces, read_latest_trace
from core.health import run_health_check
from core.intelligence.bellator_context_builder import (
    build_bellator_context_packet,
    build_bellator_diagnostics_payload,
)
from core.data_sources.health import build_data_sources_status
from core.logging import log_decision_trace, log_error, log_event
from core.manual_visual_review import manual_visual_review_summary
from core.memory.context import build_context_packet, context_status
from core.memory.session import upsert_session_record
from core.models import NodeIdentity, TribunalResult, Vote, VoteValue
from core.paths import EXPORT_DIR, HISTORY_PATH, SYSTEM_LOG_PATH, SYSTEM_ROOT
from core.proposals.store import (
    archive_proposal,
    create_proposal,
    duplicate_proposal,
    list_recent_proposals,
    proposal_history_status,
    resend_proposal,
)
from core.proposals.lifecycle import link_decision_trace_to_proposal, proposal_lifecycle_summary
from core.proposals.templates import get_template, list_templates, render_template_draft
from core.export.simulation import export_simulation_dossier, latest_simulation_dossier_status
from core.simulation.registry import SCENARIO_TYPES
from core.simulation.store import (
    branches_for_scenario,
    create_stored_scenario,
    expand_stored_branch,
    get_scenario,
    get_simulation_status,
    list_recent_scenarios,
)
from core.telemetry import TELEMETRY_HISTORY, sample_telemetry
from core.tribunal import Tribunal
from core.tribunal_events import (
    TRIBUNAL_PHASES,
    append_bounded_event,
    append_reasoning_event,
    build_phase_event,
    convergence_percent,
    phase_for_verdict,
    theme_reasoning_phrase,
)
from core.voting.engine import ConsensusEngine
from core.voting.orchestrator import VotingOrchestrator
from core.voting.rules import ConsensusRules
from integrations.msty.runtime import MstyRuntime
from core.export.dossier import export_dossier, latest_dossier_export_status
from core.export.verdict import export_latest_verdict, latest_verdict_export_status
from tools.export_runtime_bundle import export_runtime_bundle
from tools.provider_status_report import build_provider_status_report
from tools.runtime_snapshot import build_runtime_snapshot, health_badge_from_snapshot
from tools.verify_active_manifest import verify_active_manifest
from voice.arbiter_verdict_voice import dispatch_arbiter_verdict_voice, voice_status_snapshot
from ui.animations.typewriter import reveal_text_with_cursor_sync
from ui.assets.app_icon import apply_app_icon_to_page
from ui.assets.registry import get_theme_layout_metadata
from ui.components.header import build_header
from ui.components.log_panel import build_log_panel
from ui.components.monolith_panel import build_monolith_panel, card_border, VERDICT_FEEDBACK_SECONDS
from ui.components.proposal_panel import build_proposal_panel
from ui.components.proposal_panel import EMPTY_PROPOSAL_HINT
from ui.components.status_panel import build_status_panel
from ui.components.telemetry_panel import build_telemetry_panel, telemetry_graph_lines, telemetry_summary_lines
from ui.components.theme_switcher import build_theme_switcher
from ui.components.verdict_panel import build_verdict_panel
from ui.layout_contract import CENTER_COLUMN_FLEX, FOOTER_HEIGHT, LEFT_COLUMN_FLEX, PROPOSAL_HEIGHT, RIGHT_COLUMN_FLEX
from ui.themes.catalog import THEMES, get_gui_theme_options, resolve_theme_key
from ui.war_room_runtime import (
    append_timeline,
    ambient_message,
    build_runtime_details,
    cursor_frame,
    default_activity_states,
    default_latencies,
    detect_proposal_file_change,
    log_war_room_runtime,
    proposal_lifecycle_events,
    transition_state,
)


GUI_ACTIVITY_REFRESH_INTERVAL_SECONDS = 6.0
GUI_PROVIDER_REFRESH_INTERVAL_SECONDS = 30.0
GUI_INTERACTION_HOLD_SECONDS = 12.0
GUI_WINDOW_MODES = ("maximized", "fullscreen", "windowed")
GuiWindowMode = Literal["maximized", "fullscreen", "windowed"]
LIFECYCLE_IDLE = "IDLE"
LIFECYCLE_PROPOSAL_RECEIVED = "CLASSIFYING"
LIFECYCLE_DISPATCHING = "DISPATCHING"
LIFECYCLE_ANALYZING = "ANALYZING"
LIFECYCLE_DELIBERATING = "DELIBERATING"
LIFECYCLE_VOTES_RECEIVED = "DELIBERATING"
LIFECYCLE_SYNTHESIZING = "SYNTHESIZING"
LIFECYCLE_CONSENSUS_REACHED = "CONSENSUS_REACHED"
LIFECYCLE_NO_CONSENSUS = "NO_CONSENSUS"
LIFECYCLE_ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
LIFECYCLE_VERDICT_ISSUED = "EXPORT_READY"
LIFECYCLE_ERROR_DEGRADED = "ESCALATION_REQUIRED"
LIFECYCLE_STATES = TRIBUNAL_PHASES
VOTE_STATUS_VALUES = {value.value for value in VoteValue}
GuiUpdateCallback = Callable[[], None]
HEARTBEAT_MESSAGES = (
    "MONOLITH LINK STABLE",
    "MEMORY INDEX READY",
    "PROVIDER CHECK PENDING",
    "TRIBUNAL IDLE",
)
COMMAND_PALETTE_ACTIONS = (
    "Runtime Snapshot",
    "Provider Status",
    "Latest Verdict",
    "Open Diagnostics",
    "Open DIRECTORATE",
    "Export Runtime Bundle",
    "Run Verification",
    "Verify Integrity",
    "Visual Review Status",
    "Telemetry Snapshot",
    "Proposal History",
    "Export Latest Verdict",
    "Create Simulation",
    "View Simulations",
    "Export Simulation Dossier",
    "Refresh Data Sources",
    "View Source Health",
    "View Bellator Intel Feed",
    "View Aeternum Market Feed",
    "Toggle Theme",
    "Open Decision Trace Viewer",
)


def ensure_flet_desktop_runtime() -> None:
    if importlib.util.find_spec("flet_desktop") is not None:
        return
    flet_version = getattr(ft, "__version__", None)
    package = f"flet-desktop=={flet_version}" if flet_version else "flet-desktop"
    raise RuntimeError(
        "Flet desktop runtime is not installed in this Python environment. "
        f"Run `python -m pip install -e .` or `python -m pip install {package}` "
        "from the active CONSENSUS virtual environment, then restart the app."
    )


@dataclass
class GuiState:
    theme_key: str
    config: RuntimeConfig
    nodes: Dict[str, NodeIdentity]
    compact_header: bool = True
    provider_status: Dict[str, object] = field(default_factory=lambda: {"status": "unknown"})
    memory_status: str = "UNKNOWN"
    monolith_statuses: Dict[str, str] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    recent_decisions: List[str] = field(default_factory=list)
    current_proposal: str = ""
    proposal_input_text: str = ""
    proposal_template_id: str = ""
    last_proposal_record_id: str = ""
    current_result: TribunalResult | None = None
    window_mode: GuiWindowMode = "maximized"
    lifecycle_state: str = LIFECYCLE_IDLE
    monolith_vote_details: Dict[str, Dict[str, object]] = field(default_factory=dict)
    displayed_synthesis: str = "ARBITER synthesis channel idle."
    displayed_confidence: float = 0.0
    provider_warning: str = ""
    heartbeat_index: int = 0
    heartbeat_text: str = HEARTBEAT_MESSAGES[0]
    session_memory_status: str = "ACTIVE"
    context_retrieval_status: str = "NONE"
    prior_decisions_used: int = 0
    context_summary: str = ""
    aurelius_runtime: AureliusRuntime | None = None
    aurelius_voice_loop_enabled: bool = False
    pulse_index: int = 0
    cursor_visible: bool = True
    consensus_locked: bool = False
    timeline_events: List[str] = field(default_factory=list)
    lifecycle_events: List[Dict[str, object]] = field(default_factory=list)
    lifecycle_phase_started_at: float = 0.0
    phase_durations: Dict[str, float] = field(default_factory=dict)
    reasoning_stream: List[str] = field(default_factory=list)
    convergence_percent: float = 0.0
    monolith_activity_states: Dict[str, str] = field(default_factory=default_activity_states)
    monolith_latencies_ms: Dict[str, int] = field(default_factory=default_latencies)
    proposal_file_mtime: float | None = None
    ui_interaction_hold_until: float = 0.0
    bellator_intelligence_diagnostics: Dict[str, object] = field(default_factory=dict)
    render_in_progress: bool = False
    render_lock: Any = field(default_factory=threading.RLock, repr=False)
    live_panels: Dict[str, Any] = field(default_factory=dict, repr=False)
    diagnostics_drawer_open: bool = False
    command_palette_open: bool = False
    trace_viewer_open: bool = False
    proposal_history_open: bool = False
    visual_review_viewer_open: bool = False
    telemetry_viewer_open: bool = False
    simulation_viewer_open: bool = False
    simulation_create_open: bool = False
    branch_tree_viewer_open: bool = False
    selected_simulation_id: str = ""
    selected_simulation_branch_id: str = ""
    simulation_branch_expand_open: bool = False
    data_sources_viewer_open: bool = False
    data_sources_viewer_mode: str = "health"
    trace_filter: str = ""
    operator_status: str = "OPERATOR READY"
    runtime_snapshot_cache: Dict[str, Any] = field(default_factory=dict)
    telemetry_snapshot: Dict[str, Any] = field(default_factory=dict)
    directorate: Directorate = field(default_factory=Directorate, repr=False)
    directorate_boot_open: bool = False
    directorate_open: bool = False
    directorate_busy: bool = False
    directorate_initialized: bool = False
    directorate_config_failed: bool = False
    directorate_config_path: Path | None = None
    directorate_config_loader: Callable[[], RuntimeConfig] | None = field(default=None, repr=False)
    directorate_animation: bool = True
    reduced_motion: bool = False
    directorate_collapsed: bool = True
    directorate_cable: bool = False
    directorate_session_id: str = ""
    directorate_sources: List[Dict[str, str]] = field(default_factory=list)
    submission_lock: Any = field(default_factory=threading.Lock, repr=False)
    ui_stopped: Any = field(default_factory=threading.Event, repr=False)
    narrow_layout: bool = False
    proposal_expanded: bool = False
    proposal_regions: tuple[Any, Any] | None = field(default=None, repr=False)
    proposal_input_focused: bool = False
    proposal_actions_hovered: bool = False
    submission_message: str = ""
    watch_deliberation: bool = False
    deliberation_viewer_open: bool = False
    deliberation_records: List[Dict[str, Any]] = field(default_factory=list)
    deliberation_pending: Dict[str, str] = field(default_factory=dict)
    monolith_feedback: Dict[str, tuple[str, float]] = field(default_factory=dict)

    @property
    def theme(self):
        return THEMES[self.theme_key]


def create_gui_state(
    theme_key: str,
    config: RuntimeConfig,
    nodes: Dict[str, NodeIdentity] | None = None,
    compact_header: bool = True,
    window_mode: GuiWindowMode = "maximized",
    initialize: bool = True,
) -> GuiState:
    resolved = resolve_theme_key(theme_key)
    if resolved not in THEMES:
        raise RuntimeError(f"Unknown GUI theme: {theme_key}")
    active_nodes = nodes or apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    config.theme = resolved
    state = GuiState(
        theme_key=resolved,
        config=config,
        nodes=active_nodes,
        compact_header=compact_header,
        window_mode=window_mode,
    )
    preferences = read_preferences()
    state.directorate_animation = preferences.get("animation", True)
    state.reduced_motion = preferences.get("reduced_motion", False)
    # Start folded on every launch; unfold only when the operator requests it.
    state.directorate_collapsed = True
    state.directorate_cable = preferences.get("cable", False)
    state.watch_deliberation = preferences.get("watch_deliberation", False)
    for component in STARTUP_COMPONENTS:
        state.directorate.emit(component, "STARTUP_CHECK", "PENDING", "Awaiting check", check=True)
    state.directorate.emit("CONFIG", "STARTUP_CHECK", "AVAILABLE", "Runtime configuration loaded", check=True)
    if initialize:
        initialize_directorate(state)
    state.heartbeat_text = ambient_message(state.theme_key, state.pulse_index)
    state.timeline_events = [
        append_timeline([], "SYSTEM", f"{state.theme.display_name} interface online")[0]
    ]
    refresh_bellator_intelligence_status(state)
    log_war_room_runtime("gui_state_created", {"theme": state.theme_key, "window_mode": window_mode})
    return state


def initialize_directorate(state: GuiState, on_update: GuiUpdateCallback | None = None) -> None:
    """Run on a worker in the desktop entry point; never delay for animation."""
    state.directorate_busy = True
    def check(component: str, status: str, summary: str) -> None:
        state.directorate.emit(component, "STARTUP_CHECK", status, summary, check=True)
        _notify(on_update)
    try:
        if state.directorate_config_failed:
            check("CONFIG", "RUNNING", "Retrying configuration load")
            try:
                from config.runtime import load_runtime_config
                config = state.directorate_config_loader() if state.directorate_config_loader else load_runtime_config(state.directorate_config_path)
                if str(config.startup_theme).upper() != "RANDOM" and resolve_theme_key(config.startup_theme) not in THEMES:
                    raise ValueError("Unknown startup theme")
                config.theme = state.theme_key
                state.nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
                state.config = config
                state.directorate_config_failed = False
                check("CONFIG", "AVAILABLE", "Runtime configuration loaded")
            except Exception as exc:
                check("CONFIG", "FAILED", f"Configuration unreadable ({type(exc).__name__}); correct it locally and retry")
                return
        check("PROVIDER", "RUNNING", "Querying provider health and model inventory")
        try:
            refresh_gui_status(state)
            status, summary = provider_observation(state.provider_status, state.config.backend == "mock")
            check("PROVIDER", status, summary)
        except Exception as exc:
            check("PROVIDER", "FAILED", f"Provider check failed ({type(exc).__name__}); retry available")
        check("MEMORY", "RUNNING", "Reading local decision and session stores")
        try:
            from core.paths import SESSION_MEMORY_PATH
            stores = ((HISTORY_PATH, list), (SESSION_MEMORY_PATH, dict))
            present = 0
            for path, shape in stores:
                if path.exists():
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(payload, shape):
                        raise ValueError("Invalid memory shape")
                    present += 1
            check("MEMORY", "AVAILABLE" if present == 2 else "DEGRADED",
                  "Local decision/session stores readable" if present == 2 else "Local stores not yet complete; no external MNEMOSYNE connection")
        except Exception as exc:
            check("MEMORY", "FAILED", f"Local memory unreadable ({type(exc).__name__}); existing data preserved")
        check("AURELIUS", "RUNNING", "Inspecting local runtime capabilities")
        try:
            state.aurelius_runtime = get_aurelius_runtime()
            capabilities = state.aurelius_runtime.status()
            check("AURELIUS", "DEGRADED" if capabilities.get("agent_setup_error") else "AVAILABLE",
                  f"Local runtime constructed; agent enabled: {bool(capabilities.get('agent_enabled'))}; "
                  f"voice input: {bool(capabilities.get('voice_adapter_available'))}; TTS: {bool(capabilities.get('tts_available'))}")
        except Exception as exc:
            check("AURELIUS", "FAILED", f"Local runtime unavailable ({type(exc).__name__})")
        refresh_telemetry_for_gui(state)
        state.directorate_initialized = True
    finally:
        state.directorate_busy = False
        _notify(on_update)


def save_directorate_preferences(state: GuiState) -> None:
    write_preferences({"animation": state.directorate_animation, "reduced_motion": state.reduced_motion,
                       "cable": state.directorate_cable,
                       "watch_deliberation": state.watch_deliberation})


def set_aurelius_voice_loop(state: GuiState, enabled: bool) -> None:
    state.aurelius_voice_loop_enabled = bool(enabled)
    if state.aurelius_runtime is not None:
        state.aurelius_runtime.set_voice_loop(state.aurelius_voice_loop_enabled)
    log_event(
        "gui_aurelius_voice_loop",
        {"enabled": state.aurelius_voice_loop_enabled, "theme": state.theme_key},
    )


def _provider_is_degraded(provider_status: Dict[str, object]) -> bool:
    return str(provider_status.get("status", "unknown")).lower() != "ready"


def _fallback_warning(state: GuiState, runtime: MstyRuntime) -> str:
    if state.config.backend == "mock":
        return "SIMULATION ONLY - NO REAL MODEL CALLS"
    policy = state.provider_status.get("fallback_policy", {}) if isinstance(state.provider_status, dict) else {}
    if isinstance(policy, dict) and policy.get("mode") == "real_model_fallback":
        return "PREFERRED MODELS UNAVAILABLE - REAL FALLBACK MODELS WILL KEEP EACH MONOLITH'S ROLE"
    if _provider_is_degraded(state.provider_status):
        return "PROVIDER DEGRADED - DELIBERATION REQUIRES AN AVAILABLE REAL MODEL"
    return ""


def runtime_snapshot_from_gui_state(state: GuiState) -> Dict[str, Any]:
    provider_payload = state.provider_status.get("provider", state.provider_status) if isinstance(state.provider_status, dict) else {}
    if not isinstance(provider_payload, dict):
        provider_payload = {}
    visual_review = manual_visual_review_summary()
    snapshot = {
        "version": SYSTEM_VERSION,
        "backend": state.config.backend,
        "provider_status": provider_payload.get("status") or state.provider_status.get("status", "unknown"),
        "active_models": provider_payload.get("models", []),
        "missing_models": provider_payload.get("missing_required_models", {}),
        "degraded_reason": provider_payload.get("degraded_reason") or state.provider_status.get("error"),
        "war_room_layout_guard": {
            "main_column_expand": [LEFT_COLUMN_FLEX, CENTER_COLUMN_FLEX, RIGHT_COLUMN_FLEX],
            "proposal_height": PROPOSAL_HEIGHT,
            "footer_height": FOOTER_HEIGHT,
            "footer_fixed": True,
            "diagnostics_overlay": True,
        },
        "render_guard_status": {
            "enabled": True,
            "state_field": "render_in_progress",
            "reentrant_event": "ui_render_skipped_reentrant",
        },
        "latest_decision_trace": read_latest_trace(),
        "latest_runtime_log": None,
        "test_manifest_path": str(latest_test_manifest_path()),
        "integrity_status": verify_active_manifest(),
        "screenshot_status": visual_review.get("screenshot_status", "MANUAL_REVIEW_REQUIRED"),
        "visual_review": visual_review,
        "telemetry": state.telemetry_snapshot or sample_telemetry(TELEMETRY_HISTORY),
        "voice_status": voice_status_snapshot(),
        "proposal_history_status": proposal_history_status(),
        "latest_verdict_export": latest_verdict_export_status(),
        "proposal_lifecycle_summary": proposal_lifecycle_summary(),
        "latest_dossier_export": latest_dossier_export_status(),
        "simulation_status": get_simulation_status(),
        "latest_simulation_dossier": latest_simulation_dossier_status(),
        "tribunal_lifecycle": {
            "current_phase": state.lifecycle_state,
            "event_count": len(state.lifecycle_events),
            "phase_durations": dict(state.phase_durations),
            "convergence_percent": state.convergence_percent,
            "reasoning_stream_size": len(state.reasoning_stream),
        },
    }
    snapshot["health_badge"] = health_badge_from_snapshot(snapshot)
    return snapshot


def refresh_telemetry_for_gui(state: GuiState) -> Dict[str, Any]:
    state.telemetry_snapshot = sample_telemetry(TELEMETRY_HISTORY)
    return state.telemetry_snapshot


def refresh_gui_status(state: GuiState, preserve_monolith_state: bool = True) -> None:
    runtime = MstyRuntime(state.config)
    previous_provider = state.provider_status.get("provider", state.provider_status)
    previous_backend = previous_provider.get("active_backend") or previous_provider.get("backend")
    try:
        state.provider_status = runtime.health_check()
    except Exception as exc:
        log_error("gui_provider_status_error", exc)
        state.provider_status = {"status": "degraded", "error": str(exc)}
    current_provider = state.provider_status.get("provider", state.provider_status)
    if isinstance(current_provider, dict):
        current_backend = current_provider.get("active_backend") or current_provider.get("backend")
        if previous_backend and current_backend and previous_backend != current_backend:
            log_event(
                "provider_runtime_switch",
                {"previous_backend": previous_backend, "active_backend": current_backend},
                level="INFO",
            )
    state.memory_status = _memory_status_text()
    provider_payload = state.provider_status.get("provider", {}) if isinstance(state.provider_status, dict) else {}
    model_status = provider_payload.get("model_status", {}) if isinstance(provider_payload, dict) else {}
    base_statuses = {
        **{key: "ONLINE" for key in TRIBUNAL_AGENT_IDS},
        ARBITER: "DEGRADED" if state.provider_status.get("status") != "ready" else "ONLINE",
    }
    for agent_id, status in model_status.items():
        if status in {"missing", "offline"} and agent_id in base_statuses:
            base_statuses[agent_id] = "DEGRADED"
    if preserve_monolith_state:
        for key, value in state.monolith_statuses.items():
            if value in {"THINKING", "QUEUED", *VOTE_STATUS_VALUES}:
                base_statuses[key] = value
    state.monolith_statuses = base_statuses
    missing_models = provider_payload.get("missing_required_models", {}) if isinstance(provider_payload, dict) else {}
    for agent_id, model in missing_models.items():
        if agent_id in base_statuses and agent_id not in state.monolith_vote_details:
            state.monolith_vote_details[agent_id] = {
                "confidence": 0.0,
                "response_time": 0.0,
                "reasoning": f"Required model unavailable: {model}",
            }
    state.provider_warning = _fallback_warning(state, runtime)
    if state.directorate_initialized:
        status, summary = provider_observation(state.provider_status, state.config.backend == "mock")
        previous = next((e for e in state.directorate.checks() if e.component == "PROVIDER"), None)
        if previous is None or previous.status != status:
            state.directorate.emit("PROVIDER", "PROVIDER_STATUS_CHANGED", status, summary, check=True)
    state.runtime_snapshot_cache = runtime_snapshot_from_gui_state(state)
    state.logs = read_recent_log_events()
    state.recent_decisions = read_recent_decisions()
    refresh_bellator_intelligence_status(state)


def refresh_bellator_intelligence_status(state: GuiState) -> Dict[str, object]:
    state.bellator_intelligence_diagnostics = build_bellator_diagnostics_payload()
    return state.bellator_intelligence_diagnostics


def refresh_bellator_intelligence_for_gui(state: GuiState) -> Dict[str, object]:
    packet = build_bellator_context_packet("GUI manual Bellator intelligence diagnostics refresh")
    state.bellator_intelligence_diagnostics = build_bellator_diagnostics_payload(packet)
    log_event(
        "gui_bellator_intelligence_refresh",
        {
            "mode": packet.get("mode"),
            "sources": {
                source: payload.get("status")
                for source, payload in packet.get("sources", {}).items()
                if isinstance(payload, dict)
            },
        },
    )
    return state.bellator_intelligence_diagnostics


def recheck_provider_for_gui(state: GuiState) -> Dict[str, object]:
    refresh_gui_status(state)
    log_event("gui_provider_recheck", {"theme": state.theme_key, "status": state.provider_status})
    return state.provider_status


def advance_gui_heartbeat(state: GuiState) -> str:
    state.heartbeat_index = (state.heartbeat_index + 1) % len(HEARTBEAT_MESSAGES)
    state.heartbeat_text = HEARTBEAT_MESSAGES[state.heartbeat_index]
    return state.heartbeat_text


def advance_war_room_activity(state: GuiState) -> None:
    if state.reduced_motion or not state.directorate_animation:
        state.cursor_visible = False
    else:
        state.pulse_index += 1
        state.cursor_visible = cursor_frame(state.pulse_index) == "_"
    state.heartbeat_text = ambient_message(state.theme_key, state.pulse_index)
    state.monolith_latencies_ms = {
        agent_id: default_latencies(state.pulse_index)[agent_id]
        for agent_id in state.monolith_activity_states
    }
    if state.directorate_animation and not state.reduced_motion and state.pulse_index % 8 == 0:
        append_timeline(state.timeline_events, "SYSTEM", state.heartbeat_text)
        log_war_room_runtime("ambient_heartbeat", {"theme": state.theme_key, "message": state.heartbeat_text})
    changed, next_mtime = detect_proposal_file_change(state.proposal_file_mtime)
    if next_mtime is not None:
        state.proposal_file_mtime = next_mtime
    if changed:
        for event in proposal_lifecycle_events()[:2]:
            append_timeline(state.timeline_events, "PROPOSAL", event.lower())
        log_war_room_runtime("proposal_file_changed", {"theme": state.theme_key})


def submit_proposal_for_gui(state: GuiState, proposal: str) -> TribunalResult:
    return submit_proposal_live_for_gui(state, proposal, skip_animations=True)


def _notify(on_update: GuiUpdateCallback | None) -> None:
    if on_update is not None:
        on_update()


def _vote_detail(vote: Vote) -> Dict[str, object]:
    return {
        "argument": vote.argument, "peer_responses": vote.peer_responses,
        "review_required": vote.review_required, "review_reason": vote.review_reason,
        "vote_change_reason": vote.vote_change_reason, "unresolved_disagreements": vote.unresolved_disagreements,
        "vote": vote.vote.value,
        "confidence": vote.confidence,
        "evidence_quality": vote.evidence_quality,
        "critical_risk": vote.critical_risk,
        "critical_domain_relevance": vote.critical_domain_relevance,
        "validation_errors": list(vote.validation_errors),
        "reasoning": vote.reasoning,
        "response_time": vote.response_time,
        "model": vote.model,
        "backend": vote.backend,
    }


def _set_lifecycle(state: GuiState, lifecycle_state: str, on_update: GuiUpdateCallback | None = None) -> None:
    previous = state.lifecycle_state
    previous_started = state.lifecycle_phase_started_at
    event = build_phase_event(lifecycle_state, previous_phase=previous, previous_started_at=previous_started)
    if previous and event.previous_duration_seconds:
        state.phase_durations[previous] = state.phase_durations.get(previous, 0.0) + event.previous_duration_seconds
    state.lifecycle_state = lifecycle_state
    state.lifecycle_phase_started_at = float(event.started_at)
    append_bounded_event(state.lifecycle_events, event)
    append_reasoning_event(state.reasoning_stream, theme_reasoning_phrase(state.theme_key, lifecycle_state))
    append_timeline(state.timeline_events, "LIFECYCLE", lifecycle_state.lower())
    log_war_room_runtime(
        "tribunal_phase_transition",
        {
            "state": lifecycle_state,
            "previous_state": previous,
            "previous_duration_seconds": event.previous_duration_seconds,
            "theme": state.theme_key,
        },
    )
    log_event(
        "tribunal_phase_transition",
        {
            "state": lifecycle_state,
            "previous_state": previous,
            "previous_duration_seconds": event.previous_duration_seconds,
            "theme": state.theme_key,
        },
    )
    _notify(on_update)


def _animate_confidence(
    state: GuiState,
    target_confidence: float,
    on_update: GuiUpdateCallback | None = None,
    steps: int = 8,
    delay: float = 0.025,
) -> None:
    if steps <= 1 or delay <= 0:
        state.displayed_confidence = target_confidence
        _notify(on_update)
        return
    for index in range(1, steps + 1):
        state.displayed_confidence = target_confidence * (index / steps)
        _notify(on_update)
        time.sleep(delay)


def submit_proposal_live_for_gui(
    state: GuiState,
    proposal: str,
    on_update: GuiUpdateCallback | None = None,
    skip_animations: bool = False,
) -> TribunalResult:
    clean_proposal = proposal.strip()
    if not clean_proposal:
        raise ValueError("Proposal is empty.")
    skip_animations = skip_animations or state.reduced_motion or not state.directorate_animation
    state.directorate_session_id = uuid.uuid4().hex[:12]
    state.directorate_sources = []
    state.directorate.emit("TRIBUNAL", "PROPOSAL_RECEIVED", "RUNNING", "Proposal accepted for deliberation", state.directorate_session_id)
    state.current_proposal = clean_proposal
    state.proposal_input_text = clean_proposal
    state.current_result = None
    state.deliberation_records = []
    state.deliberation_pending = {}
    state.monolith_feedback = {}
    state.monolith_vote_details = {}
    state.displayed_synthesis = ""
    state.displayed_confidence = 0.0
    state.provider_warning = ""
    state.consensus_locked = False
    state.lifecycle_events = []
    state.lifecycle_phase_started_at = 0.0
    state.phase_durations = {}
    state.reasoning_stream = []
    state.convergence_percent = 0.0
    for agent_id in [*TRIBUNAL_AGENT_IDS, ARBITER]:
        state.monolith_activity_states[agent_id] = "IDLE"
    _set_lifecycle(state, LIFECYCLE_PROPOSAL_RECEIVED, on_update)
    append_timeline(state.timeline_events, "PROPOSAL", "received vote package")
    log_event("gui_proposal_submitted", {"theme": state.theme_key, "query": clean_proposal})
    log_war_room_runtime("proposal_received", {"theme": state.theme_key, "query": clean_proposal})
    taxonomy_hint = ""
    source = "manual"
    title = None
    if state.proposal_template_id:
        try:
            template = get_template(state.proposal_template_id)
            taxonomy_hint = str(template.get("default_taxonomy_hint", ""))
            title = str(template.get("title", ""))
            source = "template"
        except KeyError:
            taxonomy_hint = ""
    proposal_record = create_proposal(
        title=title,
        body=clean_proposal,
        taxonomy_hint=taxonomy_hint,
        source=source,
        template_id=state.proposal_template_id or None,
        status="SUBMITTED",
    )
    state.last_proposal_record_id = str(proposal_record["proposal_id"])
    runtime = MstyRuntime(state.config)
    state.provider_warning = _fallback_warning(state, runtime)
    rules = ConsensusRules(
        minimum_confidence=state.config.minimum_confidence,
        quorum=state.config.quorum,
        majority=state.config.majority,
        high_risk_review=state.config.high_risk_review,
        evidence_threshold=state.config.evidence_threshold,
        classification_confidence_threshold=state.config.classification_confidence_threshold,
        tie_break_priority=state.config.tie_break_priority,
        proposal_taxonomy=state.config.proposal_taxonomy,
        monolith_domain_map=state.config.monolith_domain_map,
    )
    session_id = state.directorate_session_id
    started = time.perf_counter()
    memory_context = build_context_packet(clean_proposal)
    _set_lifecycle(state, LIFECYCLE_DISPATCHING, on_update)
    state.prior_decisions_used = int(memory_context.get("prior_decisions_used", 0) or 0)
    state.context_retrieval_status = context_status(memory_context)
    state.context_summary = str(memory_context.get("summary", "No prior decisions retrieved."))
    state.directorate_sources = retrieved_sources(memory_context)
    if state.prior_decisions_used:
        state.directorate.emit("MEMORY", "MEMORY_RECALLED", "AVAILABLE",
                              f"Retrieved {state.prior_decisions_used} local prior decisions", session_id)
    for reference in state.directorate_sources:
        state.directorate.emit("REFERENCES", "SOURCE_FOUND", "AVAILABLE", "Attributed reference retrieved", session_id)
    votes: Dict[str, Vote] = {}
    state.monolith_statuses = {
        **{key: "QUEUED" for key in TRIBUNAL_AGENT_IDS},
        ARBITER: "ONLINE" if state.provider_status.get("status") == "ready" else "DEGRADED",
    }
    for agent_id in TRIBUNAL_AGENT_IDS:
        transition_state(
            state.monolith_activity_states,
            agent_id,
            "IDLE",
            state.timeline_events,
            "loaded vote package",
        )
    _set_lifecycle(state, LIFECYCLE_ANALYZING, on_update)
    log_event(
        "proposal",
        {"session_id": session_id, "theme": state.theme_key, "sequential": state.config.sequential, "query": clean_proposal},
    )

    orchestrator = VotingOrchestrator(state.nodes, runtime)
    current_round_votes: Dict[str, Vote] = {}
    reported_substitutions: set[tuple[str, str]] = set()

    def on_deliberation_event(event: Dict[str, Any]) -> None:
        phase = str(event["phase"])
        event_type = event["type"]
        if event_type == "round_started":
            state.directorate.emit("TRIBUNAL", "ROUND_STARTED", "RUNNING", f"Round {event['round']}/3: {phase}", session_id)
            current_round_votes.clear()
            if phase == "critique":
                _set_lifecycle(state, LIFECYCLE_DELIBERATING, on_update)
            append_reasoning_event(state.reasoning_stream, f"Round {event['round']}/3: {phase}")
        elif event_type == "agent_started":
            agent_id = str(event["agent_id"])
            state.deliberation_pending = {**state.deliberation_pending, agent_id: f"round {event['round']} / {phase}"}
            state.directorate.emit(agent_id, "MODEL_STARTED", "RUNNING", f"{phase} role execution started", session_id)
            state.monolith_statuses[agent_id] = "THINKING"
            transition_state(state.monolith_activity_states, agent_id, "ANALYZING", state.timeline_events, f"{phase} round")
            packet = event["context"].get("bellator_context_packet")
            for reference in retrieved_sources(event["context"]):
                if reference not in state.directorate_sources:
                    state.directorate_sources.append(reference)
                    state.directorate.emit("REFERENCES", "SOURCE_FOUND", "AVAILABLE", "Attributed reference retrieved", session_id)
            if agent_id == BELLATOR and isinstance(packet, dict):
                state.bellator_intelligence_diagnostics = build_bellator_diagnostics_payload(packet)
        elif event_type == "vote_received":
            agent_id = str(event["agent_id"])
            vote = event["vote"]
            preferred = state.nodes[agent_id].model
            substitution = (agent_id, vote.model)
            if (not vote.validation_errors and vote.model != preferred
                    and state.config.backend != "mock" and vote.backend != "mock"
                    and substitution not in reported_substitutions):
                reported_substitutions.add(substitution)
                state.directorate.emit(agent_id, "MODEL_SUBSTITUTED", "DEGRADED",
                    f"Preferred model {preferred}; executing with {vote.model}. Role instructions retained.", session_id)
            state.deliberation_records = [*state.deliberation_records,
                assessment_record(vote, int(event["round"]), phase,
                                  simulation=state.config.backend == "mock" or vote.backend == "mock")][-12:]
            state.deliberation_pending = {key: value for key, value in state.deliberation_pending.items() if key != agent_id}
            state.monolith_feedback = {**state.monolith_feedback, agent_id:
                ("ERROR" if vote.validation_errors else vote.vote.value, time.monotonic() + VERDICT_FEEDBACK_SECONDS)}
            state.directorate.emit(agent_id, "ASSESSMENT_FAILED" if vote.validation_errors else "ASSESSMENT_RECEIVED",
                                  "FAILED" if vote.validation_errors else "AVAILABLE",
                                  f"{phase}: {vote.vote.value}" + ("; response validation failed" if vote.validation_errors else ""), session_id)
            if vote.unresolved_disagreements or any(peer.get("stance") in {"challenge", "reject"} for peer in vote.peer_responses):
                state.directorate.emit(agent_id, "DISSENT_FILED", "AVAILABLE", f"Explicit peer dissent recorded in {phase}", session_id)
            if vote.review_required:
                state.directorate.emit(agent_id, "REVIEW_REQUESTED", "DEGRADED", "Explicit review request recorded", session_id)
            current_round_votes[agent_id] = vote
            state.convergence_percent = convergence_percent(current_round_votes)
            state.monolith_statuses[agent_id] = "ERROR" if vote.validation_errors else vote.vote.value
            state.monolith_vote_details[agent_id] = _vote_detail(vote)
            state.monolith_activity_states[agent_id] = "ERROR" if vote.validation_errors else "IDLE"
            append_reasoning_event(state.reasoning_stream, f"{agent_id} {phase}: {vote.reasoning}")
            if vote.argument:
                append_reasoning_event(state.reasoning_stream, f"{agent_id} claim: {vote.argument['claim']}")
                for evidence in vote.argument.get("evidence", []):
                    append_reasoning_event(state.reasoning_stream, f"{agent_id} evidence ({evidence['source']}): {evidence['detail']}")
                append_reasoning_event(state.reasoning_stream, f"{agent_id} strongest objection: {vote.argument['strongest_objection']}")
            for peer in vote.peer_responses:
                append_reasoning_event(state.reasoning_stream, f"{agent_id} {peer['stance']} {peer['peer']} claim: {peer['reason']}")
            if vote.review_required:
                append_reasoning_event(state.reasoning_stream, f"{agent_id} requests review: {vote.review_reason}")
            if vote.vote_change_reason:
                append_reasoning_event(state.reasoning_stream, f"{agent_id} decision change: {vote.vote_change_reason}")
            append_timeline(state.timeline_events, agent_id, f"{phase}: {vote.vote.value.lower()} confidence {vote.confidence:.0%}")
            execution = runtime.last_execution.get(agent_id, {})
            if execution.get("model_fallback"):
                append_reasoning_event(state.reasoning_stream, f"{agent_id} uses fallback model {vote.model} with its assigned role and settings")
            if vote.validation_errors:
                state.provider_warning = f"DELIBERATION INCOMPLETE: {agent_id} {phase} failed. {vote.reasoning}"
        _notify(on_update)

    try:
        votes = orchestrator.cast_votes(
            clean_proposal, session_id, state.theme_key, state.config.sequential,
            memory_context, on_event=on_deliberation_event,
        )
        if state.lifecycle_state != LIFECYCLE_DELIBERATING:
            _set_lifecycle(state, LIFECYCLE_DELIBERATING, on_update)
        state.monolith_statuses[ARBITER] = "THINKING"
        transition_state(
            state.monolith_activity_states,
            ARBITER,
            "SYNCHRONIZING",
            state.timeline_events,
            "synchronizing consensus",
        )
        _set_lifecycle(state, LIFECYCLE_SYNTHESIZING, on_update)
        result = ConsensusEngine(rules, state.theme_key).calculate_result(clean_proposal, votes, session_id)
        orchestrator.attach_audit(result)
        state.directorate.record_decision(result, list(state.directorate_sources))
        terminal_phase = phase_for_verdict(result.verdict, result.terminal_branch, result.review_triggers)
        state.directorate.emit(ARBITER, terminal_phase, "AVAILABLE" if terminal_phase == "CONSENSUS_REACHED" else "DEGRADED",
                              f"Explicit final verdict: {result.verdict.value}" + (" / SIMULATION ONLY" if result.simulation else ""), session_id)
        _set_lifecycle(state, terminal_phase, on_update)
        state.current_result = result
        state.monolith_statuses[ARBITER] = result.verdict.value
        state.monolith_feedback = {key: (status, time.monotonic() + VERDICT_FEEDBACK_SECONDS)
                                   for key, status in state.monolith_statuses.items()}
        _animate_confidence(
            state,
            result.confidence,
            on_update,
            steps=1 if skip_animations else 10,
            delay=0 if skip_animations else 0.025,
        )

        def update_synthesis(text: str) -> None:
            state.displayed_synthesis = text
            _notify(on_update)

        reveal_text_with_cursor_sync(
            result.reason,
            on_update=update_synthesis,
            speed=0 if skip_animations else 0.012,
            skip=skip_animations,
            lock_text="[CONSENSUS LOCKED]" if terminal_phase == "CONSENSUS_REACHED" else "[VERDICT RECORDED]",
        )
        state.displayed_synthesis = result.reason
        state.consensus_locked = terminal_phase == "CONSENSUS_REACHED"
        state.monolith_activity_states[ARBITER] = "IDLE"
        append_timeline(state.timeline_events, ARBITER, "consensus locked" if state.consensus_locked else "verdict recorded without consensus lock")
        setattr(result, "lifecycle_events", list(state.lifecycle_events))
        setattr(result, "phase_durations", dict(state.phase_durations))
        setattr(result, "reasoning_stream", list(state.reasoning_stream))
        setattr(result, "convergence_percent", state.convergence_percent)
        record_result(result)
        state.directorate.emit("LOCAL ARCHIVE", "DECISION_SAVED", "AVAILABLE", "Decision saved in local history", session_id)
        log_decision_trace(result)
        try:
            trace = read_latest_trace()
            link_result = link_decision_trace_to_proposal(
                trace if isinstance(trace, dict) else {
                    "proposal_id": result.session_id,
                    "session_id": result.session_id,
                    "taxonomy": result.proposal_classification,
                    "votes": {
                        agent_id: {
                            "vote": vote.vote.value,
                            "confidence": vote.confidence,
                            "evidence_quality": vote.evidence_quality,
                            "critical_risk": vote.critical_risk,
                            "model": vote.model,
                        }
                        for agent_id, vote in result.votes.items()
                    },
                    "final_verdict": result.verdict.value,
                    "confidence": result.confidence,
                    "terminal_branch": result.terminal_branch,
                    "review_triggers": result.review_triggers,
                    "timestamp": result.timestamp,
                },
                proposal_id=state.last_proposal_record_id,
            )
            state.runtime_snapshot_cache["proposal_lifecycle_summary"] = proposal_lifecycle_summary()
            state.runtime_snapshot_cache["latest_verdict_export"] = latest_verdict_export_status()
            state.runtime_snapshot_cache["latest_dossier_export"] = latest_dossier_export_status()
            append_timeline(state.timeline_events, "PROPOSAL", f"linked {link_result.get('decision_status', 'decision')}")
        except Exception as exc:
            log_event(
                "gui_proposal_history_update_failed",
                {"proposal_id": state.last_proposal_record_id, "error": str(exc)},
                level="WARN",
            )
        provider_payload = state.provider_status.get("provider", state.provider_status)
        try:
            upsert_session_record(
                {
                    "session_id": result.session_id,
                    "active_theme": result.theme,
                    "proposal": result.query,
                    "monolith_votes": {
                        agent_id: {
                            "vote": vote.vote.value,
                            "confidence": vote.confidence,
                            "evidence_quality": vote.evidence_quality,
                            "critical_risk": vote.critical_risk,
                            "critical_domain_relevance": vote.critical_domain_relevance,
                            "validation_errors": vote.validation_errors,
                            "reasoning": vote.reasoning,
                            "model": vote.model,
                            "response_time": vote.response_time,
                        }
                        for agent_id, vote in result.votes.items()
                    },
                    "arbiter_verdict": result.verdict.value,
                    "verdict": result.verdict.value,
                    "synthesis_summary": result.reason,
                    "deliberation_transcript": result.deliberation_transcript,
                    "deliberation_complete": result.deliberation_complete,
                    "simulation": result.simulation,
                    "terminal_branch": result.terminal_branch,
                    "proposal_classification": result.proposal_classification,
                    "provider_backend": provider_payload.get("active_backend") if isinstance(provider_payload, dict) else None,
                    "provider_status": provider_payload.get("status") if isinstance(provider_payload, dict) else None,
                    "model_mapping": {agent_id: vote.model for agent_id, vote in result.votes.items()},
                    "timestamp": result.timestamp,
                    "tags": [],
                    "context": {
                        "retrieval": memory_context.get("retrieval"),
                        "prior_decisions_used": memory_context.get("prior_decisions_used", 0),
                        "items": memory_context.get("items", []),
                    },
                }
            )
            state.directorate.emit("MEMORY", "SESSION_SAVED", "AVAILABLE", "Local session memory updated", session_id)
        except Exception as exc:
            log_event("gui_session_memory_write_failed", {"session_id": result.session_id, "error": str(exc)}, level="WARN")
            state.directorate.emit("MEMORY", "SESSION_SAVE_FAILED", "FAILED", "Local session write failed; decision history remains separate", session_id)
        log_event(
            "verdict",
            {
                "session_id": session_id,
                "verdict": result.verdict.value,
                "confidence": result.confidence,
                "review_triggers": result.review_triggers,
                "terminal_branch": result.terminal_branch,
                "elapsed": round(time.perf_counter() - started, 6),
            },
        )
        if state.config.backend != "mock":
            dispatch_arbiter_verdict_voice(result, async_dispatch=True, enabled=True)
            state.runtime_snapshot_cache["voice_status"] = voice_status_snapshot()
        _set_lifecycle(state, LIFECYCLE_VERDICT_ISSUED, on_update)
        state.logs = read_recent_log_events()
        state.recent_decisions = read_recent_decisions()
        log_event("gui_verdict_update", {"session_id": result.session_id, "verdict": result.verdict.value})
        return result
    except Exception as exc:
        state.directorate.emit("TRIBUNAL", "PROCESSING_FAILED", "FAILED", f"Submission failed ({type(exc).__name__})", session_id)
        _set_lifecycle(state, LIFECYCLE_ERROR_DEGRADED, None)
        for agent_id in [*TRIBUNAL_AGENT_IDS, ARBITER]:
            state.monolith_activity_states[agent_id] = "ERROR"
        state.monolith_statuses = {agent_id: "ERROR" for agent_id in [*TRIBUNAL_AGENT_IDS, ARBITER]}
        state.monolith_feedback = {agent_id: ("ERROR", time.monotonic() + VERDICT_FEEDBACK_SECONDS)
                                   for agent_id in state.monolith_statuses}
        state.deliberation_pending = {}
        error = f"{type(exc).__name__}: {exc}"
        append_timeline(state.timeline_events, "ERROR", f"Submission failed: {error}")
        log_war_room_runtime("proposal_lifecycle_error", {"theme": state.theme_key, "error": error}, level="ERROR")
        state.displayed_synthesis = f"SUBMISSION FAILED\n{error}"
        state.provider_warning = state.provider_warning or f"SUBMISSION FAILED: {error}"
        _notify(on_update)
        raise


def read_recent_log_events(limit: int = 12) -> List[str]:
    if not SYSTEM_LOG_PATH.exists():
        return []
    lines = SYSTEM_LOG_PATH.read_text(encoding="utf-8").splitlines()[-limit:]
    events: List[str] = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = str(record.get("timestamp", ""))[11:19] or "--:--:--"
        level = str(record.get("level", "INFO")).upper()
        if level == "WARNING":
            level = "WARN"
        events.append(f"[{timestamp}] {level} {record.get('event_type', 'event')}")
    return events


def read_recent_decisions(limit: int = 6) -> List[str]:
    if not HISTORY_PATH.exists():
        return []
    try:
        records = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    decisions: List[str] = []
    for item in records[-limit:]:
        decisions.append(f"{item.get('verdict', 'UNKNOWN')} | {item.get('theme', '--')} | {item.get('session_id', '--')}")
    return decisions


def export_decision_history() -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = EXPORT_DIR / f"decision_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if HISTORY_PATH.exists():
        shutil.copy2(HISTORY_PATH, target)
    else:
        target.write_text("[]\n", encoding="utf-8")
    log_event("gui_export_decision_history", {"path": str(target)})
    return target


def export_session_logs() -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = EXPORT_DIR / f"session_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    if SYSTEM_LOG_PATH.exists():
        shutil.copy2(SYSTEM_LOG_PATH, target)
    else:
        target.write_text("", encoding="utf-8")
    log_event("gui_export_session_logs", {"path": str(target)})
    return target


def open_theme_preview_folder() -> Path:
    path = SYSTEM_ROOT / "_ARBITER" / "theme_previews"
    path.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
    except Exception:
        pass
    log_event("gui_open_theme_preview_folder", {"path": str(path)})
    return path


def latest_test_manifest_path() -> Path:
    return Path("reports") / f"verification_v{SYSTEM_VERSION}.json"


def filter_decision_traces(traces: List[Dict[str, Any]], proposal_id: str = "") -> List[Dict[str, Any]]:
    needle = proposal_id.strip().lower()
    if not needle:
        return traces
    return [trace for trace in traces if needle in str(trace.get("proposal_id", "")).lower()]


def latest_verdict_text(state: GuiState) -> str:
    if state.current_result is not None:
        return state.current_result.verdict.value
    trace = read_latest_trace()
    if isinstance(trace, dict):
        return str(trace.get("final_verdict") or trace.get("verdict") or "--")
    return "--"


def execute_command_palette_action(state: GuiState, action: str) -> str:
    if action not in COMMAND_PALETTE_ACTIONS:
        raise ValueError(f"Unknown command palette action: {action}")
    try:
        if action == "Runtime Snapshot":
            state.runtime_snapshot_cache = build_runtime_snapshot()
            message = "Runtime snapshot refreshed"
        elif action == "Provider Status":
            state.runtime_snapshot_cache["provider_status_report"] = build_provider_status_report()
            message = "Provider status report refreshed"
        elif action == "Latest Verdict":
            message = f"Latest verdict: {latest_verdict_text(state)}"
        elif action == "Open Diagnostics":
            state.diagnostics_drawer_open = True
            message = "Diagnostics opened"
        elif action == "Open DIRECTORATE":
            state.directorate_open = True
            message = "DIRECTORATE dispatch desk opened"
        elif action == "Export Runtime Bundle":
            target = export_runtime_bundle()
            message = f"Runtime bundle exported: {target}"
        elif action == "Run Verification":
            completed = subprocess.run(
                [sys.executable, str(SYSTEM_ROOT / "tools" / "run_tests.py")],
                cwd=SYSTEM_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            message = f"Verification {'passed' if completed.returncode == 0 else 'failed'}: {latest_test_manifest_path()}"
        elif action == "Verify Integrity":
            result = verify_active_manifest()
            state.runtime_snapshot_cache["integrity_status"] = result
            message = f"Integrity {result.get('status', 'UNKNOWN')}"
        elif action == "Visual Review Status":
            state.runtime_snapshot_cache["visual_review"] = manual_visual_review_summary()
            state.visual_review_viewer_open = True
            message = "Visual review status opened"
        elif action == "Telemetry Snapshot":
            state.telemetry_snapshot = sample_telemetry(TELEMETRY_HISTORY)
            state.runtime_snapshot_cache["telemetry"] = state.telemetry_snapshot
            state.telemetry_viewer_open = True
            message = "Telemetry snapshot opened"
        elif action == "Proposal History":
            state.proposal_history_open = True
            state.runtime_snapshot_cache["proposal_history_status"] = proposal_history_status()
            message = "Proposal history opened"
        elif action == "Export Latest Verdict":
            result = export_latest_verdict()
            state.runtime_snapshot_cache["latest_verdict_export"] = latest_verdict_export_status()
            message = f"Latest verdict exported: {result['json_path']}"
        elif action == "Create Simulation":
            state.simulation_create_open = True
            message = "Simulation creation opened"
        elif action == "View Simulations":
            state.runtime_snapshot_cache["simulation_status"] = get_simulation_status()
            state.simulation_viewer_open = True
            message = "Simulation registry opened"
        elif action == "Export Simulation Dossier":
            scenario_id = state.selected_simulation_id or str(get_simulation_status().get("latest_simulation_id") or "")
            if not scenario_id:
                raise RuntimeError("No simulation is available for export.")
            exported = export_simulation_dossier(scenario_id)
            state.runtime_snapshot_cache["latest_simulation_dossier"] = latest_simulation_dossier_status()
            message = f"Simulation dossier exported: {exported['json_path']}"
        elif action == "Refresh Data Sources":
            state.runtime_snapshot_cache["data_sources_status"] = build_data_sources_status(attempt_live=True)
            message = "Data sources refreshed with cache fallback"
        elif action == "View Source Health":
            state.runtime_snapshot_cache["data_sources_status"] = build_data_sources_status(attempt_live=False)
            state.data_sources_viewer_mode = "health"
            state.data_sources_viewer_open = True
            message = "Data source health opened"
        elif action == "View Bellator Intel Feed":
            state.runtime_snapshot_cache["data_sources_status"] = build_data_sources_status(attempt_live=False)
            state.data_sources_viewer_mode = "bellator"
            state.data_sources_viewer_open = True
            message = "Bellator intel feed opened"
        elif action == "View Aeternum Market Feed":
            state.runtime_snapshot_cache["data_sources_status"] = build_data_sources_status(attempt_live=False)
            state.data_sources_viewer_mode = "aeternum"
            state.data_sources_viewer_open = True
            message = "Aeternum market feed opened"
        elif action == "Toggle Theme":
            options = [theme.key for theme in get_gui_theme_options()]
            index = options.index(state.theme_key) if state.theme_key in options else -1
            state.theme_key = options[(index + 1) % len(options)]
            state.config.theme = state.theme_key
            state.heartbeat_text = ambient_message(state.theme_key, state.pulse_index)
            message = f"Theme toggled: {state.theme_key}"
        else:
            state.trace_viewer_open = True
            message = "Decision trace viewer opened"
        state.operator_status = message
        log_event("gui_command_palette_action", {"action": action, "status": message, "theme": state.theme_key})
        return message
    except Exception as exc:
        log_error("gui_command_palette_action_error", exc, {"action": action, "theme": state.theme_key})
        state.operator_status = f"{action} failed: {exc}"
        raise


def set_diagnostics_drawer_open(state: GuiState, open_state: bool | None = None) -> bool:
    next_state = (not state.diagnostics_drawer_open) if open_state is None else bool(open_state)
    if state.diagnostics_drawer_open == next_state:
        return state.diagnostics_drawer_open
    state.diagnostics_drawer_open = next_state
    state.ui_interaction_hold_until = time.monotonic() + GUI_INTERACTION_HOLD_SECONDS
    if "telemetry" not in state.runtime_snapshot_cache:
        state.runtime_snapshot_cache["telemetry"] = state.telemetry_snapshot
    if "proposal_history_status" not in state.runtime_snapshot_cache:
        state.runtime_snapshot_cache["proposal_history_status"] = proposal_history_status()
    if "proposal_lifecycle_summary" not in state.runtime_snapshot_cache:
        state.runtime_snapshot_cache["proposal_lifecycle_summary"] = proposal_lifecycle_summary()
    if "latest_verdict_export" not in state.runtime_snapshot_cache:
        state.runtime_snapshot_cache["latest_verdict_export"] = latest_verdict_export_status()
    if "latest_dossier_export" not in state.runtime_snapshot_cache:
        state.runtime_snapshot_cache["latest_dossier_export"] = latest_dossier_export_status()
    if "voice_status" not in state.runtime_snapshot_cache:
        state.runtime_snapshot_cache["voice_status"] = voice_status_snapshot()
    log_event(
        "gui_diagnostics_drawer",
        {"open": state.diagnostics_drawer_open, "theme": state.theme_key, "snapshot_source": "cached"},
    )
    return state.diagnostics_drawer_open


def _memory_status_text() -> str:
    try:
        import psutil  # type: ignore

        memory = psutil.virtual_memory()
        return f"{round(memory.used / (1024**3), 1)}GB / {round(memory.total / (1024**3), 1)}GB"
    except Exception:
        return "AVAILABLE"


def _apply_page_theme(page: ft.Page, state: GuiState) -> None:
    theme = state.theme
    page.title = "CONSENSUS War Room"
    apply_app_icon_to_page(page)
    page.bgcolor = theme.background_color
    page.theme = ft.Theme(font_family=theme.font_family)
    page.scroll = None
    page.padding = 0
    page.spacing = 0


def apply_gui_window_mode(page: ft.Page, mode: GuiWindowMode = "maximized") -> None:
    if mode not in GUI_WINDOW_MODES:
        raise ValueError(f"Unknown GUI window mode: {mode}")
    fullscreen = mode == "fullscreen"
    maximized = mode == "maximized"
    window = getattr(page, "window", None)
    if window is not None:
        if hasattr(window, "full_screen"):
            window.full_screen = fullscreen
        if hasattr(window, "maximized"):
            window.maximized = maximized
        if hasattr(window, "resizable"):
            window.resizable = True
    for attr, value in (("window_full_screen", fullscreen), ("window_maximized", maximized)):
        if hasattr(page, attr):
            setattr(page, attr, value)


def build_command_palette(state: GuiState, on_action: Callable[[str], None] | None = None) -> ft.Control:
    theme = state.theme

    def run_action(action: str):
        return (lambda _: on_action(action)) if on_action is not None else None

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("COMMAND PALETTE", color=theme.accent_color, size=14, weight=ft.FontWeight.BOLD),
                        ft.Text("CTRL+K", color=theme.secondary_color, size=11),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                *[
                    ft.TextButton(
                        action,
                        on_click=run_action(action),
                        style=ft.ButtonStyle(
                            color=theme.text_color,
                            bgcolor=theme.background_color,
                            side=ft.BorderSide(1, theme.secondary_color),
                            shape=ft.RoundedRectangleBorder(radius=0),
                            padding=ft.padding.symmetric(horizontal=10, vertical=8),
                            text_style=ft.TextStyle(size=12, font_family=theme.font_family),
                        ),
                        height=38,
                    )
                    for action in COMMAND_PALETTE_ACTIONS
                ],
                ft.Text(state.operator_status, color=theme.panel_value or theme.text_color, size=10, max_lines=2),
            ],
            spacing=7,
            tight=True,
        ),
        width=460,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def build_data_sources_viewer(state: GuiState, status: Dict[str, Any] | None = None) -> ft.Control:
    theme = state.theme
    payload = status or state.runtime_snapshot_cache.get("data_sources_status") or build_data_sources_status(attempt_live=False)
    mode = state.data_sources_viewer_mode
    feeds = payload.get("feeds", {}) if isinstance(payload, dict) else {}
    feed = feeds.get(mode, {}) if mode in {"bellator", "aeternum"} else {}

    def line(value: str, color: str | None = None, bold: bool = False) -> ft.Text:
        return ft.Text(
            value,
            color=color or theme.text_color,
            size=10,
            weight=ft.FontWeight.BOLD if bold else None,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    rows: list[ft.Control] = []
    if mode == "health":
        for item in payload.get("source_health", []):
            source_status = str(item.get("status", "UNKNOWN"))
            color = theme.primary_color if source_status == "READY" else theme.warning_color
            rows.append(line(f"{item.get('source_id', '--').upper()}: {source_status}", color, True))
    else:
        rows.append(line(f"FEED STATUS: {feed.get('status', 'DATA_UNAVAILABLE')}", theme.accent_color, True))
        rows.append(line(str(feed.get("operator_note") or "No normalized source items available."), theme.panel_value or theme.text_color))
        for item in feed.get("items", [])[:16]:
            rows.append(line(f"[{item.get('source', '--')}] {item.get('title', '--')}", theme.text_color))
    if not rows:
        rows.append(line("NO DATA SOURCE STATUS AVAILABLE", theme.warning_color, True))

    return ft.Container(
        content=ft.Column(
            [
                line("DATA SOURCES STATUS", theme.accent_color, True),
                line(f"MODE: {mode.upper()} | REFRESH: CACHE ONLY", theme.secondary_color),
                ft.Column(rows, spacing=5, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            spacing=8,
            expand=True,
        ),
        width=620,
        height=520,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def build_decision_trace_viewer(
    state: GuiState,
    on_filter: Callable[[str], None] | None = None,
    traces: List[Dict[str, Any]] | None = None,
) -> ft.Control:
    theme = state.theme
    recent = traces if traces is not None else list_recent_traces(limit=25)
    visible_traces = list(reversed(filter_decision_traces(recent, state.trace_filter)))[:12]

    def update_filter(event: ft.ControlEvent) -> None:
        state.trace_filter = str(event.control.value or "")
        if on_filter is not None:
            on_filter(state.trace_filter)

    def text(value: str, color: str | None = None, size: int = 10, bold: bool = False) -> ft.Text:
        return ft.Text(
            value,
            color=color or theme.text_color,
            size=size,
            weight=ft.FontWeight.BOLD if bold else None,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    rows: list[ft.Control] = []
    for trace in visible_traces:
        proposal_id = str(trace.get("proposal_id") or "--")
        verdict = str(trace.get("final_verdict") or trace.get("verdict") or "--")
        taxonomy = str(trace.get("taxonomy") or trace.get("proposal_taxonomy") or "--")
        rows.append(
            ft.Container(
                content=ft.Column(
                    [
                        text(f"PROPOSAL {proposal_id}", theme.accent_color, bold=True),
                        text(f"VERDICT {verdict} | TAXONOMY {taxonomy}", theme.panel_value or theme.text_color),
                    ],
                    spacing=2,
                ),
                padding=6,
                border=ft.border.all(1, theme.secondary_color),
                bgcolor=theme.background_color,
            )
        )
    if not rows:
        rows.append(text("NO DECISION TRACES FOUND", theme.warning_color, bold=True))

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        text("DECISION TRACE VIEWER", theme.accent_color, size=14, bold=True),
                        text("RECENT TRACES", theme.secondary_color, size=10),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.TextField(
                    label="proposal_id filter",
                    value=state.trace_filter,
                    on_change=update_filter,
                    border_color=theme.secondary_color,
                    focused_border_color=theme.accent_color,
                    color=theme.text_color,
                    label_style=ft.TextStyle(color=theme.secondary_color, size=11),
                    text_style=ft.TextStyle(color=theme.text_color, size=12, font_family=theme.font_family),
                    height=48,
                ),
                ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            spacing=8,
            expand=True,
        ),
        width=520,
        height=560,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def build_proposal_history_viewer(
    state: GuiState,
    on_action: Callable[[str, str], None] | None = None,
    proposals: List[Dict[str, Any]] | None = None,
) -> ft.Control:
    theme = state.theme
    recent = proposals if proposals is not None else list_recent_proposals(limit=20)

    def text(value: str, color: str | None = None, size: int = 10, bold: bool = False) -> ft.Text:
        return ft.Text(
            value,
            color=color or theme.text_color,
            size=size,
            weight=ft.FontWeight.BOLD if bold else None,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    def action_button(label: str, action: str, proposal_id: str) -> ft.Control:
        handler = (lambda _: on_action(action, proposal_id)) if on_action is not None else None
        return ft.TextButton(
            label,
            on_click=handler,
            style=ft.ButtonStyle(
                color=theme.primary_color,
                bgcolor=theme.background_color,
                side=ft.BorderSide(1, theme.secondary_color),
                shape=ft.RoundedRectangleBorder(radius=0),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                text_style=ft.TextStyle(size=10, font_family=theme.font_family),
            ),
            height=30,
        )

    def status_color(status: str) -> str:
        return {
            "DECIDED": theme.primary_color,
            "NO_CONSENSUS": theme.warning_color,
            "ESCALATED": theme.warning_color,
            "ERROR": theme.error_color,
            "ARCHIVED": theme.muted_text or theme.secondary_color,
            "SUBMITTED": theme.accent_color,
            "DRAFT": theme.secondary_color,
        }.get(status.upper(), theme.secondary_color)

    def status_badge(status: str) -> ft.Control:
        color = status_color(status)
        return ft.Container(
            content=text(status.upper(), color, size=9, bold=True),
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            border=ft.border.all(1, color),
            bgcolor=theme.background_color,
            tooltip=f"Proposal decision status: {status.upper()}",
        )

    rows: list[ft.Control] = []
    for proposal in recent:
        proposal_id = str(proposal.get("proposal_id") or "--")
        status = str(proposal.get("status") or "--")
        decision_status = str(proposal.get("decision_status") or status)
        verdict_available = bool(proposal.get("linked_verdict_export_json") or proposal.get("linked_verdict_export_md"))
        verdict_text = "Verdict linked" if verdict_available else "Awaiting tribunal resolution."
        rows.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                text(str(proposal.get("created_at", "--")), theme.secondary_color),
                                status_badge(status),
                                status_badge(decision_status),
                            ],
                            spacing=6,
                        ),
                        text(str(proposal.get("title") or "Untitled Proposal"), theme.accent_color, bold=True),
                        text(f"{proposal.get('template_id') or 'manual'} | {proposal_id}", theme.panel_value or theme.text_color),
                        text(f"{proposal.get('decision_timestamp') or '--'} | {verdict_text}", status_color(decision_status)),
                        ft.Row(
                            [
                                action_button("RESEND", "resend", proposal_id),
                                action_button("DUPLICATE/EDIT", "duplicate", proposal_id),
                                action_button("REOPEN DRAFT", "reopen", proposal_id),
                                action_button("OPEN VERDICT", "open_verdict", proposal_id),
                                action_button("EXPORT DOSSIER", "export_dossier", proposal_id),
                                action_button("ARCHIVE", "archive", proposal_id),
                            ],
                            spacing=6,
                            wrap=True,
                        ),
                    ],
                    spacing=3,
                ),
                padding=7,
                border=ft.border.all(1, theme.secondary_color),
                bgcolor=theme.background_color,
            )
        )
    if not rows:
        rows.append(text("NO PROPOSAL HISTORY FOUND", theme.warning_color, bold=True))

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        text("PROPOSAL HISTORY", theme.accent_color, size=14, bold=True),
                        text("CTRL+H", theme.secondary_color, size=10),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            spacing=8,
            expand=True,
        ),
        width=620,
        height=600,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def build_visual_review_status_viewer(state: GuiState) -> ft.Control:
    theme = state.theme
    summary = state.runtime_snapshot_cache.get("visual_review")
    if not isinstance(summary, dict):
        summary = manual_visual_review_summary()

    def text(value: str, color: str | None = None, size: int = 10, bold: bool = False) -> ft.Text:
        return ft.Text(
            value,
            color=color or theme.text_color,
            size=size,
            weight=ft.FontWeight.BOLD if bold else None,
            max_lines=3,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    rows: list[ft.Control] = []
    for entry in summary.get("themes", []):
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "PENDING"))
        color = {
            "APPROVED": theme.primary_color,
            "PENDING": theme.warning_color,
            "REJECTED": theme.error_color,
            "NEEDS_FIX": theme.warning_color,
        }.get(status, theme.secondary_color)
        rows.append(
            ft.Container(
                content=ft.Column(
                    [
                        text(f"{str(entry.get('theme', '--')).upper()} | {status}", color, bold=True),
                        text(f"SHOT: {entry.get('screenshot_path', '--')}", theme.secondary_text or theme.secondary_color),
                        text(f"NOTES: {entry.get('reviewer_notes') or '--'}", theme.panel_value or theme.text_color),
                    ],
                    spacing=2,
                ),
                padding=6,
                border=ft.border.all(1, color),
                bgcolor=theme.background_color,
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        text("VISUAL REVIEW STATUS", theme.accent_color, size=14, bold=True),
                        text(str(summary.get("screenshot_status", "MANUAL_REVIEW_REQUIRED")), theme.warning_color, size=10),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                text(f"FILE: {summary.get('path', '--')}", theme.secondary_color),
                text(
                    f"PENDING: {summary.get('pending_count', 0)} | NEEDS FIX/REJECTED: {summary.get('action_required_count', 0)}",
                    theme.warning_color if summary.get("action_required_count", 0) else theme.primary_color,
                    bold=True,
                ),
                ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            spacing=8,
            expand=True,
        ),
        width=560,
        height=560,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def build_telemetry_snapshot_viewer(state: GuiState) -> ft.Control:
    theme = state.theme
    telemetry = state.telemetry_snapshot or sample_telemetry(TELEMETRY_HISTORY)

    def text(value: str, color: str | None = None, size: int = 10, bold: bool = False) -> ft.Text:
        return ft.Text(
            value,
            color=color or theme.text_color,
            size=size,
            weight=ft.FontWeight.BOLD if bold else None,
            selectable=True,
        )

    latest = telemetry.get("latest", {}) if isinstance(telemetry, dict) else {}
    timestamp = latest.get("timestamp", "--") if isinstance(latest, dict) else "--"
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        text("TELEMETRY SNAPSHOT", theme.accent_color, size=14, bold=True),
                        text(str(timestamp), theme.secondary_color, size=10),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                *[text(line, theme.panel_value or theme.text_color, size=12) for line in telemetry_summary_lines(theme.key, telemetry)],
                text("HISTORY", theme.accent_color, bold=True),
                *[text(line, theme.secondary_text or theme.secondary_color, size=11) for line in telemetry_graph_lines(theme.key, telemetry)],
            ],
            spacing=8,
            tight=True,
        ),
        width=520,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def build_simulation_create_overlay(state: GuiState, on_create=None) -> ft.Control:
    theme = state.theme
    title = ft.TextField(label="TITLE", value=(state.current_proposal.splitlines()[0][:80] if state.current_proposal else ""), dense=True)
    scenario_type = ft.Dropdown(
        label="SCENARIO TYPE",
        value="strategic_forecast",
        options=[ft.dropdown.Option(value) for value in SCENARIO_TYPES],
        dense=True,
    )
    actors = ft.TextField(label="ACTORS (comma separated)", dense=True)
    assumptions = ft.TextField(label="ASSUMPTIONS (key=value, comma separated)", dense=True)
    triggers = ft.TextField(label="TRIGGERS (comma separated)", dense=True)
    horizon = ft.TextField(label="HORIZON", value="operator_defined", dense=True)
    description = ft.TextField(label="DESCRIPTION", value=state.current_proposal, multiline=True, min_lines=3, max_lines=4)

    def submit(_: ft.ControlEvent | None = None) -> None:
        if on_create is not None:
            on_create(
                {
                    "title": title.value or "Operator Simulation Scaffold",
                    "scenario_type": scenario_type.value or "strategic_forecast",
                    "actors": _comma_values(actors.value),
                    "assumptions": _key_value_pairs(assumptions.value),
                    "triggers": _comma_values(triggers.value),
                    "timeline_horizon": horizon.value or "operator_defined",
                    "description": description.value or "",
                }
            )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("CREATE SIMULATION", color=theme.accent_color, weight=ft.FontWeight.BOLD, size=14),
                ft.Text("DETERMINISTIC SCAFFOLD - OPERATOR INPUTS ONLY", color=theme.warning_color, size=10),
                title,
                scenario_type,
                actors,
                assumptions,
                triggers,
                horizon,
                description,
                ft.TextButton("CREATE SCENARIO", on_click=submit),
            ],
            spacing=7,
            tight=True,
        ),
        width=620,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={"role": "simulation_create_overlay"},
    )


def build_branch_tree_viewer(state: GuiState, scenario_id: str | None = None, on_expand=None, on_export=None) -> ft.Control:
    theme = state.theme
    active_id = scenario_id or state.selected_simulation_id
    scenario = get_scenario(active_id) if active_id else None
    branches = list((scenario or {}).get("generated_branches", []))

    def text(value: str, color: str | None = None, bold: bool = False) -> ft.Text:
        return ft.Text(value, color=color or theme.text_color, size=10, weight=ft.FontWeight.BOLD if bold else None, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)

    rows: list[ft.Control] = []
    for branch in branches:
        branch_id = str(branch.get("branch_id") or "--")
        rows.append(
            ft.Container(
                content=ft.Column(
                    [
                        text(f"{'  ' * int(branch.get('depth', 0) or 0)}{branch_id}", theme.accent_color, True),
                        text(f"{branch.get('title', '--')} | P {branch.get('probability', '--')} | RISK {branch.get('risk_score', '--')}"),
                        text(str(branch.get("summary") or ""), theme.secondary_text or theme.secondary_color),
                        ft.TextButton("EXPAND WITH OPERATOR ASSUMPTIONS", on_click=(lambda _, value=branch_id: on_expand(value)) if on_expand else None),
                    ],
                    spacing=2,
                    tight=True,
                ),
                padding=6,
                border=ft.border.all(1, theme.secondary_color),
            )
        )
    if not rows:
        rows.append(text("NO BRANCH TREE SELECTED", theme.warning_color, True))
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        text(f"BRANCH TREE {active_id or '--'}", theme.accent_color, True),
                        ft.TextButton("EXPORT DOSSIER", on_click=(lambda _: on_export(active_id)) if on_export and active_id else None),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Column(rows, spacing=5, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            spacing=8,
            expand=True,
        ),
        width=680,
        height=560,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={"role": "branch_tree_viewer"},
    )


def build_branch_expand_overlay(state: GuiState, on_expand=None) -> ft.Control:
    theme = state.theme
    assumptions = ft.TextField(label="OPERATOR ASSUMPTIONS (key=value, comma separated)", dense=True)
    flags = ft.TextField(label="ESCALATION FLAGS (comma separated)", dense=True)
    title = ft.TextField(label="BRANCH TITLE", value="Operator Assumption Branch", dense=True)
    summary = ft.TextField(
        label="SUMMARY",
        value="Deterministic branch derived from operator-provided assumptions.",
        multiline=True,
        min_lines=2,
        max_lines=3,
    )

    def submit(_: ft.ControlEvent | None = None) -> None:
        if on_expand is not None:
            on_expand(
                {
                    "assumptions_delta": _key_value_pairs(assumptions.value),
                    "escalation_flags": _comma_values(flags.value),
                    "title": title.value or "Operator Assumption Branch",
                    "summary": summary.value or "Deterministic branch derived from operator-provided assumptions.",
                }
            )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("EXPAND BRANCH", color=theme.accent_color, weight=ft.FontWeight.BOLD, size=14),
                ft.Text(f"PARENT {state.selected_simulation_branch_id or '--'}", color=theme.secondary_text or theme.secondary_color, size=10),
                ft.Text("Operator assumptions are required. No autonomous forecast will be generated.", color=theme.warning_color, size=10),
                assumptions,
                flags,
                title,
                summary,
                ft.TextButton("EXPAND DETERMINISTIC BRANCH", on_click=submit),
            ],
            spacing=7,
            tight=True,
        ),
        width=600,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={"role": "simulation_branch_expand_overlay"},
    )


def build_simulation_viewer(state: GuiState, scenarios: List[Dict[str, Any]] | None = None, on_action=None) -> ft.Control:
    theme = state.theme
    recent = scenarios if scenarios is not None else list_recent_scenarios(limit=20)
    status = state.runtime_snapshot_cache.get("simulation_status")
    if not isinstance(status, dict):
        status = get_simulation_status()

    def text(value: str, color: str | None = None, size: int = 10, bold: bool = False) -> ft.Text:
        return ft.Text(
            value,
            color=color or theme.text_color,
            size=size,
            weight=ft.FontWeight.BOLD if bold else None,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    rows: list[ft.Control] = []
    for scenario in recent:
        scenario_id = str(scenario.get("scenario_id", "--"))
        rows.append(
            ft.Container(
                content=ft.Column(
                    [
                        text(scenario_id, theme.accent_color, bold=True),
                        text(str(scenario.get("title", "Untitled Simulation")), theme.panel_value or theme.text_color),
                        text(
                            f"{scenario.get('scenario_type', '--')} | {scenario.get('status', '--')} | proposal {scenario.get('proposal_id') or '--'}",
                            theme.secondary_text or theme.secondary_color,
                        ),
                        ft.Row(
                            [
                                ft.TextButton("OPEN TREE", on_click=(lambda _, value=scenario_id: on_action("tree", value)) if on_action else None),
                                ft.TextButton("EXPORT DOSSIER", on_click=(lambda _, value=scenario_id: on_action("export", value)) if on_action else None),
                            ],
                            spacing=6,
                        ),
                    ],
                    spacing=2,
                ),
                padding=6,
                border=ft.border.all(1, theme.secondary_color),
                bgcolor=theme.background_color,
            )
        )
    if not rows:
        rows.append(text("NO SIMULATIONS RECORDED", theme.warning_color, bold=True))

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        text("SIMULATION REGISTRY", theme.accent_color, size=14, bold=True),
                        text(str(status.get("engine_status", "READY")), theme.primary_color, size=10, bold=True),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                text(
                    f"SCENARIOS {status.get('scenario_count', 0)} | BRANCHES {status.get('branch_count', 0)} | LATEST {status.get('latest_simulation_id') or '--'}",
                    theme.panel_value or theme.text_color,
                ),
                ft.Column(rows, spacing=6, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            spacing=8,
            expand=True,
        ),
        width=600,
        height=560,
        padding=12,
        border=ft.border.all(1, theme.accent_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def _comma_values(value: str | None) -> List[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _key_value_pairs(value: str | None) -> Dict[str, str]:
    pairs: Dict[str, str] = {}
    for item in _comma_values(value):
        key, separator, raw_value = item.partition("=")
        if not separator or not key.strip() or not raw_value.strip():
            raise ValueError("Assumptions must use comma-separated key=value entries.")
        pairs[key.strip()] = raw_value.strip()
    return pairs


def _register_live_panel(state: GuiState, name: str, builder: Callable[[], ft.Control]) -> ft.Control:
    panel = builder()
    state.live_panels[name] = (panel, builder)
    return panel


def _set_proposal_editing(page: ft.Page, state: GuiState, editing: bool) -> None:
    """Resize mounted regions without replacing the input or its selection."""
    if state.ui_stopped.is_set():
        return
    with state.render_lock:
        if state.proposal_expanded == editing:
            return
        state.proposal_expanded = editing
        if state.proposal_regions is None:
            return
        proposal, verdict = state.proposal_regions
        proposal.height = None if editing else PROPOSAL_HEIGHT
        proposal.expand = True if editing else None
        verdict.visible = not editing
        verdict.expand = None if editing else True
        page.update(proposal, verdict)


def _set_submission_feedback(page: ft.Page, state: GuiState, message: str) -> None:
    state.submission_message = message
    if state.ui_stopped.is_set() or state.proposal_regions is None:
        return
    with state.render_lock:
        for control in state.proposal_regions[0].content.content.controls:
            if control.data == {"role": "proposal_submission_feedback"}:
                control.value = message or f"{EMPTY_PROPOSAL_HINT}  CTRL+ENTER = Submit."
                control.tooltip = message or None
                page.update(control)
                break


def _refresh_live_page(page: ft.Page, state: GuiState) -> None:
    """Refresh display regions without unmounting inputs, menus or overlays."""
    if state.ui_stopped.is_set():
        return
    with state.render_lock:
        panels = []
        for name, (panel, builder) in state.live_panels.items():
            fresh = builder()
            if name == "build_monolith_panel":
                # Preserve card controls so Flutter can interpolate their border colours.
                for old, new in zip(panel.controls[1:5], fresh.controls[1:5]):
                    old.content, old.border, old.animate, old.opacity = new.content, new.border, new.animate, new.opacity
                panel.controls[-1] = fresh.controls[-1]
            elif isinstance(panel, ft.Column):
                panel.controls = fresh.controls
            elif name == "build_log_panel":
                # Keep the unfolded paper and its scroll position mounted while
                # routine log/status updates replace the surrounding rows.
                old_activity = panel.content.controls[0]
                new_activity = fresh.content.controls[0]
                if (getattr(old_activity, "data", None) == getattr(new_activity, "data", None)
                        and isinstance(old_activity.data, dict)
                        and old_activity.data.get("role") == "directorate_activity"):
                    if len(old_activity.content.controls) > 1 and len(new_activity.content.controls) > 1:
                        paper = old_activity.content.controls[1]
                        fresh_paper = new_activity.content.controls[1]
                        paper.height = fresh_paper.height
                        paper.content.controls = fresh_paper.content.controls
                        new_activity.content.controls[1] = paper
                    old_activity.content.controls = new_activity.content.controls
                    fresh.content.controls[0] = old_activity
                panel.content.controls = fresh.content.controls
            else:
                panel.content = fresh.content
            panels.append(panel)
        if panels:
            page.update(*panels)


def build_gui_layout(
    state: GuiState,
    submit,
    switch_theme,
    refresh,
    run_health,
    close_gui,
    recheck_provider=None,
    toggle_aurelius_voice=None,
    refresh_bellator_intelligence=None,
    toggle_diagnostics=None,
    open_trace_viewer=None,
    on_template_select=None,
    on_proposal_change=None,
    on_footer_command=None,
    toggle_directorate=None,
    open_directorate_boot=None,
    open_directorate=None,
    toggle_cable=None,
    copy_cable=None,
    save_cable=None,
    viewport_width: float | None = None,
    on_proposal_focus=None,
    on_proposal_blur=None,
    on_proposal_tap_outside=None,
    on_proposal_actions_hover=None,
    change_watch_deliberation=None,
    open_deliberation=None,
) -> ft.Control:
    theme = state.theme

    def terminal_button(label: str, handler) -> ft.Control:
        return ft.TextButton(
            label,
            on_click=handler,
            style=ft.ButtonStyle(
                color=theme.primary_color,
                bgcolor=theme.background_color,
                side=ft.BorderSide(1, theme.secondary_color),
                shape=ft.RoundedRectangleBorder(radius=0),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                text_style=ft.TextStyle(size=12, font_family=theme.font_family),
            ),
            height=40,
        )

    def hold_footer_interaction() -> None:
        state.ui_interaction_hold_until = time.monotonic() + GUI_INTERACTION_HOLD_SECONDS

    footer_shortcuts = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    ft.Text(f"Ctrl+{key} {label}", size=11,
                            color=theme.secondary_text or theme.secondary_color,
                            font_family=theme.font_family),
                    on_click=(lambda _, key=key: on_footer_command(key)) if on_footer_command else None,
                    tooltip=f"{label} (Ctrl+{key})",
                    height=40,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    alignment=ft.alignment.center,
                    ink=True,
                    bgcolor=theme.surface_color,
                    data={"role": "footer_command", "key": key},
                )
                for key, label in (("K", "Command"), ("D", "Diagnostics"), ("P", "DIRECTORATE"), ("T", "Theme"), ("H", "History"), ("E", "Export"))
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        ),
        alignment=ft.alignment.center,
        expand=True,
        data={
            "role": "footer_shortcuts",
            "alignment": get_theme_layout_metadata(theme.key).footer_shortcut_alignment,
        },
    )
    footer_controls = ft.Row(
        [
            ft.Container(
                build_theme_switcher(theme, switch_theme, on_interaction=hold_footer_interaction),
                width=260,
                alignment=ft.alignment.center_left,
            ),
            footer_shortcuts,
            ft.Container(
                content=ft.Row(
                    [
                        terminal_button("DIAGNOSTICS", toggle_diagnostics or refresh),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0,
                    tight=True,
                ),
                width=125,
                alignment=ft.alignment.center_right,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                data={"role": "footer_aux_controls"},
            ),
        ],
        wrap=False,
        spacing=0,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        data={"role": "footer_controls"},
    )

    last_verdict = state.current_result.verdict.value if state.current_result else "--"
    session_id = state.current_result.session_id if state.current_result else "--"
    layout_meta = get_theme_layout_metadata(theme.key)
    left = ft.Container(
            _register_live_panel(state, "build_monolith_panel", lambda: build_monolith_panel(
                theme,
                state.nodes,
                state.monolith_statuses,
                vote_details=state.monolith_vote_details,
                memory_status=state.memory_status,
                provider_status=str(state.provider_status.get("status", "unknown")),
                last_verdict=state.current_result.verdict.value if state.current_result else "--",
                session_id=state.current_result.session_id if state.current_result else "--",
                lifecycle_state=state.lifecycle_state,
                runtime_details=build_runtime_details(
                    state.monolith_activity_states,
                    state.monolith_latencies_ms,
                    state.pulse_index,
                ),
                feedback=state.monolith_feedback,
                reduced_motion=state.reduced_motion or not state.directorate_animation,
        )),
        expand=LEFT_COLUMN_FLEX,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    center = ft.Container(
        ft.Column(
            [
                ft.Container(
                    build_proposal_panel(
                        theme,
                        submit,
                        initial_value=state.proposal_input_text,
                        templates=list_templates(),
                        selected_template_id=state.proposal_template_id,
                        on_template_select=on_template_select,
                        on_change=on_proposal_change,
                        expanded=state.proposal_expanded,
                        on_focus=on_proposal_focus,
                        on_blur=on_proposal_blur,
                        on_tap_outside=on_proposal_tap_outside,
                        watch_deliberation=state.watch_deliberation,
                        on_watch_change=change_watch_deliberation,
                        on_open_deliberation=open_deliberation,
                        on_actions_hover=on_proposal_actions_hover,
                        submission_message=state.submission_message,
                    ),
                    height=None if state.proposal_expanded else PROPOSAL_HEIGHT,
                    expand=True if state.proposal_expanded else None,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    data={"role": "proposal_panel_region"},
                ),
                ft.Container(
                    _register_live_panel(state, "build_verdict_panel", lambda: add_cable_controls(build_verdict_panel(
                        theme,
                        state.current_result,
                        state.current_proposal,
                        lifecycle_state=state.lifecycle_state,
                        synthesis_text=state.displayed_synthesis,
                        displayed_confidence=state.displayed_confidence,
                        prior_decisions_used=state.prior_decisions_used,
                        context_summary=state.context_summary,
                        cursor_visible=state.cursor_visible,
                        consensus_locked=state.consensus_locked,
                        lifecycle_events=state.lifecycle_events,
                        reasoning_events=state.reasoning_stream,
                        convergence_percent=state.convergence_percent,
                        phase_durations=state.phase_durations,
                    ), theme, render_cable(state.current_result, state.directorate_sources),
                        state.directorate_cable, toggle_cable, copy_cable, save_cable,
                        has_result=state.current_result is not None)),
                    expand=True if not state.proposal_expanded else None,
                    visible=not state.proposal_expanded,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    data={"role": "verdict_panel_region"},
                ),
            ],
            spacing=layout_meta.proposal_verdict_gap,
            expand=True,
        ),
        expand=CENTER_COLUMN_FLEX,
    )
    state.proposal_regions = tuple(center.content.controls)
    right = ft.Container(
        ft.Column(
            [
                ft.Container(
                    ft.Column(
                        [
                            _register_live_panel(state, "build_status_panel", lambda: build_status_panel(
                                theme,
                                state.provider_status,
                                state.memory_status,
                                lifecycle_state=state.lifecycle_state,
                                provider_warning=state.provider_warning,
                                ambient_status=state.heartbeat_text,
                                session_memory_status=state.session_memory_status,
                                context_retrieval_status=state.context_retrieval_status,
                                prior_decisions_used=state.prior_decisions_used,
                                current_session_id=state.current_result.session_id if state.current_result else "--",
                            )),
                        ],
                        spacing=8,
                        tight=True,
                        scroll=ft.ScrollMode.AUTO,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    height=240,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
                _register_live_panel(state, "build_log_panel", lambda: build_log_panel(
                    theme,
                    state.logs,
                    state.recent_decisions,
                    timeline_events=state.timeline_events,
                    bellator_intelligence=state.bellator_intelligence_diagnostics,
                    refresh_bellator_intelligence=refresh_bellator_intelligence,
                    directorate_panel=build_activity(theme, state.directorate, state.directorate_collapsed,
                                                    toggle_directorate, open_directorate),
                )),
            ],
            spacing=12,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        expand=RIGHT_COLUMN_FLEX,
    )
    narrow = viewport_width is not None and viewport_width < 1150
    if narrow:
        for region, width in zip((left, center, right), (340, 640, 340)):
            region.expand = None
            region.width = width
    body = ft.Row(
        [left, center, right],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=10,
        expand=True,
        scroll=ft.ScrollMode.AUTO if narrow else None,
    )
    footer = ft.Container(
        footer_controls,
        height=FOOTER_HEIGHT,
        padding=8,
        border=ft.border.all(1, theme.secondary_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
    shell = ft.Container(
        content=ft.Column(
            [
                _register_live_panel(state, "build_header", lambda: build_header(
                    theme,
                    str(state.provider_status.get("status", "unknown")),
                    state.memory_status,
                    state.current_result.session_id if state.current_result else "--",
                    compact=state.compact_header,
                    ambient_status=state.heartbeat_text,
                    health_badge=state.runtime_snapshot_cache.get("health_badge"),
                    telemetry=state.telemetry_snapshot,
                )),
                ft.Container(body, expand=True, padding=8, clip_behavior=ft.ClipBehavior.HARD_EDGE),
                footer,
            ],
            spacing=0,
            expand=True,
        ),
        expand=True,
        bgcolor=theme.background_color,
    )
    shell.diagnostics_drawer = build_diagnostics_drawer(state, open_trace_viewer=open_trace_viewer)  # type: ignore[attr-defined]
    shell.command_palette = build_command_palette(state)  # type: ignore[attr-defined]
    # Data-backed viewers are built only when opened in _render_page_locked.
    # Preparing invisible copies rescanned the complete decision log on every
    # footer click and kept the UI waiting for unrelated disk-backed history.
    return shell


def build_diagnostics_drawer(state: GuiState, open_trace_viewer=None, open_system_checks=None) -> ft.Control:
    theme = state.theme
    provider_payload = state.provider_status.get("provider", state.provider_status)
    if not isinstance(provider_payload, dict):
        provider_payload = {}
    endpoint_validity = provider_payload.get("health_endpoint", {}) or {}
    if not isinstance(endpoint_validity, dict):
        endpoint_validity = {}
    model_report = provider_payload.get("model_availability_report", []) or []
    active_model_lines: list[str] = []
    if isinstance(model_report, list):
        for item in model_report[:5]:
            if isinstance(item, dict):
                active_model_lines.append(
                    f"{item.get('agent_id', '--')}: {item.get('resolved_model') or item.get('required_model') or '--'}"
                )
    if not active_model_lines:
        active_model_lines = [str(model) for model in (provider_payload.get("models", []) or [])[:5]]
    last_verdict = state.current_result.verdict.value if state.current_result else "--"
    degraded_reason = str(provider_payload.get("degraded_reason") or "--")
    endpoint_status = str(endpoint_validity.get("reason") or provider_payload.get("base_url") or "--")
    integrity = state.runtime_snapshot_cache.get("integrity_status", {})
    integrity_status = str(integrity.get("status", "UNKNOWN")) if isinstance(integrity, dict) else "UNKNOWN"
    integrity_color = {
        "CLEAN": theme.primary_color,
        "DRIFT": theme.warning_color,
        "UNKNOWN": theme.muted_text or theme.secondary_color,
    }.get(integrity_status, theme.error_color)
    visual_review = state.runtime_snapshot_cache.get("visual_review")
    if not isinstance(visual_review, dict):
        visual_review = {"path": "--", "pending_count": 0, "action_required_count": 0}
    telemetry = state.telemetry_snapshot or state.runtime_snapshot_cache.get("telemetry") or {}
    proposal_status = state.runtime_snapshot_cache.get("proposal_history_status")
    if not isinstance(proposal_status, dict):
        proposal_status = {"recent_count": 0, "last_proposal_id": "--"}
    verdict_export = state.runtime_snapshot_cache.get("latest_verdict_export")
    if not isinstance(verdict_export, dict):
        verdict_export = {"latest_json": "--"}
    lifecycle = state.runtime_snapshot_cache.get("proposal_lifecycle_summary")
    if not isinstance(lifecycle, dict):
        lifecycle = {"decided_total": 0, "no_consensus_total": 0, "escalated_total": 0, "error_total": 0}
    dossier_export = state.runtime_snapshot_cache.get("latest_dossier_export")
    if not isinstance(dossier_export, dict):
        dossier_export = {"latest_json": "--"}
    voice_status = state.runtime_snapshot_cache.get("voice_status")
    if not isinstance(voice_status, dict):
        voice_status = voice_status_snapshot()
    last_voice = voice_status.get("last_voice_announcement")
    if not isinstance(last_voice, dict):
        last_voice = {}
    data_sources = state.runtime_snapshot_cache.get("data_sources_status")
    if not isinstance(data_sources, dict):
        data_sources = {"status": "UNKNOWN", "enabled_sources": []}

    def text(value: str, color: str | None = None, size: int = 10, bold: bool = False) -> ft.Text:
        return ft.Text(
            value,
            color=color or theme.text_color,
            size=size,
            weight=ft.FontWeight.BOLD if bold else None,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    return ft.Column(
        [
            ft.Row(
                [
                    text("DIAGNOSTICS", theme.accent_color, size=13, bold=True),
                    text("DRAWER", theme.panel_label or theme.secondary_color, size=10),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            text(f"PROVIDER BACKEND: {provider_payload.get('active_backend') or provider_payload.get('backend') or '--'}"),
            ft.TextButton("SYSTEM CHECKS", on_click=open_system_checks,
                          style=ft.ButtonStyle(color=theme.text_color), height=40),
            text(f"ENDPOINT STATUS: {endpoint_status}", theme.warning_color if degraded_reason != "--" else theme.text_color),
            text("ACTIVE MODELS", theme.accent_color, bold=True),
            *[text(line, theme.panel_value or theme.text_color) for line in active_model_lines[:5]],
            text(f"LAST VERDICT: {last_verdict}", theme.accent_color, bold=True),
            ft.TextButton(
                "OPEN LATEST TRACE",
                on_click=open_trace_viewer,
                style=ft.ButtonStyle(
                    color=theme.text_color,
                    bgcolor=theme.background_color,
                    side=ft.BorderSide(1, theme.secondary_color),
                    shape=ft.RoundedRectangleBorder(radius=0),
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    text_style=ft.TextStyle(size=11, font_family=theme.font_family),
                ),
                height=34,
            ),
            text(f"LAST TEST MANIFEST: {latest_test_manifest_path()}"),
            text(f"PROPOSAL HISTORY: {proposal_status.get('recent_count', 0)} recent | {proposal_status.get('last_proposal_id') or '--'}"),
            text(
                f"LIFECYCLE: DECIDED {lifecycle.get('decided_total', 0)} | NO_CONSENSUS {lifecycle.get('no_consensus_total', 0)} | ESCALATED {lifecycle.get('escalated_total', 0)} | ERROR {lifecycle.get('error_total', 0)}",
                theme.panel_value or theme.text_color,
            ),
            text(f"LATEST VERDICT EXPORT: {verdict_export.get('latest_json') or '--'}"),
            text(f"LATEST DOSSIER EXPORT: {dossier_export.get('latest_json') or '--'}"),
            text(f"ARBITER VOICE: {voice_status.get('status', 'UNKNOWN')} | {voice_status.get('backend', '--')}", theme.accent_color, bold=True),
            text(
                f"LAST VOICE: {last_voice.get('proposal_id', '--')} | {last_voice.get('terminal_state', '--')} | {last_voice.get('status', '--')}",
                theme.panel_value or theme.text_color,
            ),
            text(f"INTEGRITY STATUS: {integrity_status}", integrity_color, bold=True),
            text(
                f"DATA SOURCES: {data_sources.get('status', 'UNKNOWN')} | {', '.join(data_sources.get('enabled_sources', [])) or '--'}",
                theme.panel_value or theme.text_color,
            ),
            text(f"VISUAL REVIEW FILE: {visual_review.get('path', '--')}"),
            text(
                f"VISUAL REVIEW PENDING: {visual_review.get('pending_count', 0)} | NEEDS FIX/REJECTED: {visual_review.get('action_required_count', 0)}",
                theme.warning_color if visual_review.get("action_required_count", 0) else theme.primary_color,
                bold=True,
            ),
            text("TELEMETRY", theme.accent_color, bold=True),
            *[text(line, theme.panel_value or theme.text_color) for line in telemetry_summary_lines(theme.key, telemetry)[:5]],
            text(f"DEGRADED REASON: {degraded_reason}", theme.warning_color if degraded_reason != "--" else theme.muted_text or theme.secondary_color),
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
    )


def _render_page(page: ft.Page, state: GuiState) -> None:
    if state.ui_stopped.is_set():
        return
    with state.render_lock:
        _render_page_locked(page, state)


def _render_page_locked(page: ft.Page, state: GuiState) -> None:
    if state.render_in_progress:
        log_war_room_runtime("ui_render_skipped_reentrant", {"theme": state.theme_key}, level="WARN")
        return
    state.render_in_progress = True
    try:
        state.proposal_input_focused = False
        state.proposal_actions_hovered = False
        state.proposal_expanded = False
        _apply_page_theme(page, state)
        apply_gui_window_mode(page, state.window_mode)

        def submit(proposal: str) -> None:
            if not proposal.strip():
                _set_submission_feedback(page, state, "Enter a proposal before submitting.")
                return
            if state.directorate_config_failed:
                _set_submission_feedback(page, state, "Configuration needs attention. Open DIRECTORATE (Ctrl+P) to retry.")
                return
            if not state.submission_lock.acquire(blocking=False):
                _set_submission_feedback(page, state, "A proposal is already being reviewed. Open LIVE DELIBERATION for progress.")
                return
            state.proposal_expanded = False
            state.deliberation_viewer_open = state.watch_deliberation
            state.deliberation_records = []
            state.deliberation_pending = {}
            state.current_result = None
            state.current_proposal = proposal.strip()
            state.submission_message = "Proposal accepted. Tribunal starting..."
            def worker() -> None:
                def update() -> None:
                    _refresh_live_page(page, state)

                try:
                    submit_proposal_live_for_gui(state, proposal, on_update=update)
                    _set_submission_feedback(page, state, "Verdict recorded. See the result below.")
                except Exception as exc:
                    log_error("gui_submission_error", exc, {"theme": state.theme_key})
                    state.deliberation_pending = {}
                    state.monolith_statuses = {agent_id: "ERROR" for agent_id in [*TRIBUNAL_AGENT_IDS, ARBITER]}
                    state.monolith_feedback = {agent_id: ("ERROR", time.monotonic() + VERDICT_FEEDBACK_SECONDS)
                                               for agent_id in state.monolith_statuses}
                    state.logs = [f"ERROR gui_submission_error: {exc}", *state.logs[:10]]
                    state.directorate.emit("TRIBUNAL", "PROCESSING_FAILED", "FAILED", "Submission failed; local diagnostics available", state.directorate_session_id)
                    _set_submission_feedback(page, state, "Submission failed. Review DIRECTORATE or Diagnostics, then retry.")
                finally:
                    state.submission_lock.release()
                _refresh_live_page(page, state)

            try:
                _render_page(page, state)
                page.run_thread(worker)
            except Exception as exc:
                state.submission_lock.release()
                log_error("gui_submission_dispatch_error", exc, {"theme": state.theme_key})
                state.directorate.emit("TRIBUNAL", "PROCESSING_FAILED", "FAILED", "Could not start submission; retry available")
                _set_submission_feedback(page, state, "Could not start submission. Please retry or open Diagnostics.")

        def switch_theme(next_theme: str) -> None:
            resolved = resolve_theme_key(next_theme)
            if resolved in THEMES:
                state.theme_key = resolved
                state.config.theme = resolved
                state.heartbeat_text = ambient_message(state.theme_key, state.pulse_index)
                append_timeline(state.timeline_events, "SYSTEM", f"theme switched to {state.theme.display_name}")
                _render_page(page, state)

        def refresh(_: ft.ControlEvent | None = None) -> None:
            retry_directorate()

        def recheck_provider(_: ft.ControlEvent | None = None) -> None:
            retry_directorate()

        def retry_directorate(_: ft.ControlEvent | None = None) -> None:
            if state.directorate_busy:
                return
            state.directorate_busy = True
            _render_page(page, state)
            page.run_thread(initialize_directorate, state, lambda: _refresh_live_page(page, state))

        def preference_update() -> None:
            try:
                save_directorate_preferences(state)
            except OSError:
                state.directorate.emit("INTERFACE", "PREFERENCE_SAVE_FAILED", "FAILED", "Preferences apply for this session; local save failed")
            _render_page(page, state)

        def toggle_directorate(_=None) -> None:
            state.directorate_collapsed = not state.directorate_collapsed
            _render_page(page, state)

        def toggle_cable(_=None) -> None:
            state.directorate_cable = not state.directorate_cable
            preference_update()

        def handle_proposal_focus(_=None) -> None:
            state.proposal_input_focused = True
            state.proposal_actions_hovered = False
            _set_proposal_editing(page, state, True)

        def handle_proposal_blur(_=None) -> None:
            state.proposal_input_focused = False
            if not state.proposal_actions_hovered:
                _set_proposal_editing(page, state, False)

        def handle_proposal_tap_outside(event) -> None:
            # Flutter emits this on pointer down. Keep the action target fixed
            # until its click is delivered; blank/action-row space is outside.
            if state.proposal_actions_hovered:
                return
            state.proposal_input_focused = False
            event.control.blur()
            _set_proposal_editing(page, state, False)

        def handle_proposal_actions_hover(event) -> None:
            state.proposal_actions_hovered = str(event.data).lower() == "true"
            if not state.proposal_actions_hovered and not state.proposal_input_focused:
                _set_proposal_editing(page, state, False)

        def change_watch_deliberation(event) -> None:
            state.watch_deliberation = bool(event.control.value)
            # Save without rebuilding the editor (and disturbing typing focus).
            try:
                save_directorate_preferences(state)
            except OSError:
                state.directorate.emit("INTERFACE", "PREFERENCE_SAVE_FAILED", "FAILED", "Watch option applies for this session")
            state.proposal_input_focused = False
            state.proposal_actions_hovered = False
            _set_proposal_editing(page, state, False)

        def open_deliberation(_=None) -> None:
            state.deliberation_viewer_open = True
            _render_page(page, state)

        def close_deliberation(_=None) -> None:
            state.deliberation_viewer_open = False
            _render_page(page, state)

        def open_directorate_boot(_=None) -> None:
            state.diagnostics_drawer_open = False
            state.directorate_open = False
            state.directorate_boot_open = True
            _render_page(page, state)

        def open_directorate(_=None) -> None:
            state.directorate_open = True
            _render_page(page, state)

        def close_directorate(_=None) -> None:
            state.directorate_open = False
            _render_page(page, state)

        def directorate_history(_=None) -> None:
            state.directorate_open = False
            state.proposal_history_open = True
            _render_page(page, state)

        def copy_latest_dispatch(_=None) -> None:
            dispatches = state.directorate.dispatches()
            if dispatches:
                dispatch = dispatches[-1]
                page.set_clipboard(dispatch.report)
                state.directorate.emit("INTERFACE", "REPORT_COPIED", "AVAILABLE", "Dispatch copied to clipboard", dispatch.session_id)
                _refresh_live_page(page, state)

        def export_latest_dispatch(_=None) -> None:
            dispatches = state.directorate.dispatches()
            if not dispatches:
                return
            dispatch = dispatches[-1]
            def worker() -> None:
                try:
                    path = export_dispatch(dispatch)
                    state.directorate.emit("LOCAL ARCHIVE", "REPORT_ARCHIVED", "AVAILABLE", f"Dispatch exported locally: {path.name}", dispatch.session_id)
                except Exception:
                    state.directorate.emit("LOCAL ARCHIVE", "REPORT_EXPORT_FAILED", "FAILED", "Dispatch export failed; retry available", dispatch.session_id)
                _refresh_live_page(page, state)
            page.run_thread(worker)

        def continue_directorate(_=None) -> None:
            if not state.directorate_config_failed:
                state.directorate_boot_open = False
                _render_page(page, state)

        def change_animation(event) -> None:
            state.directorate_animation = bool(event.control.value)
            preference_update()

        def change_motion(event) -> None:
            state.reduced_motion = bool(event.control.value)
            state.cursor_visible = False
            preference_update()

        def copy_cable(_=None) -> None:
            if state.current_result:
                page.set_clipboard(render_cable(state.current_result, state.directorate_sources))
                state.directorate.emit("INTERFACE", "REPORT_COPIED", "AVAILABLE", "Cable copied to clipboard", state.current_result.session_id)
                _refresh_live_page(page, state)

        def save_cable(_=None) -> None:
            if state.current_result is None:
                return
            result = state.current_result
            sources = list(state.directorate_sources)
            def worker() -> None:
                try:
                    path = export_cable(result, sources)
                    state.directorate.emit("LOCAL ARCHIVE", "REPORT_ARCHIVED", "AVAILABLE", f"Cable exported locally: {path.name}", result.session_id)
                except Exception as exc:
                    state.directorate.emit("LOCAL ARCHIVE", "REPORT_EXPORT_FAILED", "FAILED", f"Cable export failed ({type(exc).__name__}); retry available", result.session_id)
                _refresh_live_page(page, state)
            page.run_thread(worker)

        def refresh_bellator_intelligence(_: ft.ControlEvent | None = None) -> None:
            refresh_bellator_intelligence_for_gui(state)
            _render_page(page, state)

        def toggle_aurelius_voice(event: ft.ControlEvent) -> None:
            set_aurelius_voice_loop(state, bool(event.control.value))
            _render_page(page, state)

        def run_health(_: ft.ControlEvent | None = None) -> None:
            report = run_health_check()
            state.logs = [f"HEALTH {report['status'].upper()}", *state.logs[:10]]
            _render_page(page, state)

        def close_diagnostics(_: ft.ControlEvent | None = None) -> None:
            set_diagnostics_drawer_open(state, False)
            _render_page(page, state)

        def toggle_diagnostics(_: ft.ControlEvent | None = None) -> None:
            set_diagnostics_drawer_open(state)
            _render_page(page, state)

        def open_trace_viewer(_: ft.ControlEvent | None = None) -> None:
            state.trace_viewer_open = True
            log_event("gui_decision_trace_viewer", {"open": True, "theme": state.theme_key})
            _render_page(page, state)

        def handle_template_select(template_id: str) -> None:
            state.proposal_template_id = template_id
            if template_id:
                state.proposal_input_text = render_template_draft(template_id)
            state.operator_status = f"Template loaded: {template_id or 'manual'}"
            _render_page(page, state)

        def handle_proposal_change(value: str) -> None:
            state.proposal_input_text = value
            if state.submission_message and not state.submission_lock.locked():
                _set_submission_feedback(page, state, "")

        def handle_proposal_history_action(action: str, proposal_id: str) -> None:
            try:
                if action == "resend":
                    record = resend_proposal(proposal_id)
                    state.last_proposal_record_id = str(record.get("proposal_id") or "")
                    state.operator_status = f"Proposal resent: {state.last_proposal_record_id}"
                elif action in {"duplicate", "reopen"}:
                    record = duplicate_proposal(proposal_id)
                    state.proposal_input_text = str(record.get("body") or "")
                    state.proposal_template_id = str(record.get("template_id") or "")
                    state.last_proposal_record_id = str(record.get("proposal_id") or "")
                    state.operator_status = f"Draft reopened: {state.last_proposal_record_id}" if action == "reopen" else f"Draft duplicated: {state.last_proposal_record_id}"
                elif action == "open_verdict":
                    proposal = next((item for item in list_recent_proposals(5000, include_archived=True) if item.get("proposal_id") == proposal_id), None)
                    verdict_path = str((proposal or {}).get("linked_verdict_export_md") or (proposal or {}).get("linked_verdict_export_json") or "")
                    state.operator_status = f"Verdict: {verdict_path or 'Awaiting tribunal resolution.'}"
                elif action == "export_dossier":
                    result = export_dossier(proposal_id)
                    state.runtime_snapshot_cache["latest_dossier_export"] = latest_dossier_export_status()
                    state.operator_status = f"Dossier exported: {result['markdown_path']}"
                elif action == "archive":
                    archive_proposal(proposal_id)
                    state.operator_status = f"Proposal archived: {proposal_id}"
                state.runtime_snapshot_cache["proposal_history_status"] = proposal_history_status()
                state.runtime_snapshot_cache["proposal_lifecycle_summary"] = proposal_lifecycle_summary()
            except Exception as exc:
                state.operator_status = f"Proposal history action failed: {exc}"
                log_error("gui_proposal_history_action_error", exc, {"action": action, "proposal_id": proposal_id})
            _render_page(page, state)

        def handle_simulation_create(values: Dict[str, Any]) -> None:
            try:
                scenario = create_stored_scenario(
                    **values,
                    proposal_id=state.last_proposal_record_id or None,
                    branch_depth=1,
                    status="DRAFT",
                )
                state.selected_simulation_id = scenario.scenario_id
                state.simulation_create_open = False
                state.simulation_viewer_open = True
                state.runtime_snapshot_cache["simulation_status"] = get_simulation_status()
                state.operator_status = f"Simulation created: {scenario.scenario_id}"
            except Exception as exc:
                state.operator_status = f"Simulation creation failed: {exc}"
                log_error("gui_simulation_create_error", exc)
            _render_page(page, state)

        def handle_simulation_action(action: str, scenario_id: str) -> None:
            state.selected_simulation_id = scenario_id
            try:
                if action == "tree":
                    state.branch_tree_viewer_open = True
                    state.operator_status = f"Branch tree opened: {scenario_id}"
                elif action == "export":
                    exported = export_simulation_dossier(scenario_id)
                    state.runtime_snapshot_cache["latest_simulation_dossier"] = latest_simulation_dossier_status()
                    state.operator_status = f"Simulation dossier exported: {exported['json_path']}"
            except Exception as exc:
                state.operator_status = f"Simulation action failed: {exc}"
                log_error("gui_simulation_action_error", exc, {"action": action, "scenario_id": scenario_id})
            _render_page(page, state)

        def handle_branch_expand_request(branch_id: str) -> None:
            state.selected_simulation_branch_id = branch_id
            state.simulation_branch_expand_open = True
            _render_page(page, state)

        def handle_branch_expand(values: Dict[str, Any]) -> None:
            try:
                branch = expand_stored_branch(
                    state.selected_simulation_id,
                    state.selected_simulation_branch_id,
                    **values,
                )
                state.simulation_branch_expand_open = False
                state.runtime_snapshot_cache["simulation_status"] = get_simulation_status()
                state.operator_status = f"Branch expanded: {branch.branch_id}"
            except Exception as exc:
                state.operator_status = f"Branch expansion failed: {exc}"
                log_error("gui_simulation_branch_expand_error", exc)
            _render_page(page, state)

        def handle_simulation_export(scenario_id: str) -> None:
            handle_simulation_action("export", scenario_id)

        def handle_command_action(action: str) -> None:
            state.command_palette_open = False
            if action in {"Export Runtime Bundle", "Run Verification", "Verify Integrity", "Export Latest Verdict", "Refresh Data Sources"}:
                state.operator_status = f"{action} running"
                _render_page(page, state)

                def worker() -> None:
                    try:
                        execute_command_palette_action(state, action)
                    except Exception:
                        pass
                    _render_page(page, state)

                page.run_thread(worker)
                return
            execute_command_palette_action(state, action)
            _render_page(page, state)

        def handle_trace_filter(value: str) -> None:
            state.trace_filter = value
            _render_page(page, state)

        def handle_footer_command(key: str) -> None:
            state.proposal_input_focused = False
            state.proposal_actions_hovered = False
            _set_proposal_editing(page, state, False)
            if key == "K":
                state.command_palette_open = not state.command_palette_open
                log_event(
                    "gui_command_palette",
                    {"open": state.command_palette_open, "theme": state.theme_key},
                )
                _render_page(page, state)
            elif key == "D":
                toggle_diagnostics(None)
            elif key == "P":
                state.directorate_open = not state.directorate_open
                _render_page(page, state)
            elif key == "T":
                execute_command_palette_action(state, "Toggle Theme")
                _render_page(page, state)
            elif key == "H":
                state.proposal_history_open = not state.proposal_history_open
                _render_page(page, state)
            elif key == "E":
                try:
                    execute_command_palette_action(state, "Export Latest Verdict")
                except Exception:
                    pass
                _render_page(page, state)
                _set_submission_feedback(page, state, state.operator_status)

        def on_keyboard_event(event) -> None:
            key = str(getattr(event, "key", "") or "").upper()
            if getattr(event, "ctrl", False) or getattr(event, "meta", False):
                if key in {"ENTER", "RETURN", "NUMPAD ENTER"}:
                    submit(state.proposal_input_text)
                else:
                    handle_footer_command(key)

        if hasattr(page, "on_keyboard_event"):
            page.on_keyboard_event = on_keyboard_event

        def on_resized(_=None) -> None:
            if state.ui_stopped.is_set():
                return
            narrow = bool(getattr(page, "width", 0) and page.width < 1150)
            if narrow != state.narrow_layout:
                state.narrow_layout = narrow
                _render_page(page, state)

        if hasattr(page, "on_resized"):
            page.on_resized = on_resized
        state.narrow_layout = bool(getattr(page, "width", 0) and page.width < 1150)

        state.live_panels.clear()
        layout = build_gui_layout(
            state,
            submit,
            switch_theme,
            refresh,
            run_health,
            lambda _: page.close(),
            recheck_provider=recheck_provider,
            toggle_aurelius_voice=toggle_aurelius_voice,
            refresh_bellator_intelligence=refresh_bellator_intelligence,
            toggle_diagnostics=toggle_diagnostics,
            open_trace_viewer=open_trace_viewer,
            on_template_select=handle_template_select,
            on_proposal_change=handle_proposal_change,
            on_footer_command=handle_footer_command,
            toggle_directorate=toggle_directorate,
            open_directorate_boot=open_directorate_boot,
            open_directorate=open_directorate,
            toggle_cable=toggle_cable,
            copy_cable=copy_cable,
            save_cable=save_cable,
            viewport_width=getattr(page, "width", None),
            on_proposal_focus=handle_proposal_focus,
            on_proposal_blur=handle_proposal_blur,
            on_proposal_tap_outside=handle_proposal_tap_outside,
            on_proposal_actions_hover=handle_proposal_actions_hover,
            change_watch_deliberation=change_watch_deliberation,
            open_deliberation=open_deliberation,
        )
        page.controls.clear()
        page.add(layout)
        overlay = getattr(page, "overlay", None)
        if isinstance(overlay, list):
            operator_overlays = {
                "diagnostics_drawer",
                "command_palette",
                "decision_trace_viewer",
                "proposal_history_viewer",
                "visual_review_status",
                "telemetry_snapshot",
                "simulation_viewer",
                "simulation_create_overlay",
                "branch_tree_viewer",
                "simulation_branch_expand_overlay",
                "data_sources_viewer",
                "directorate_boot",
                "directorate_desk",
                "live_deliberation",
            }
            overlay[:] = [control for control in overlay if getattr(control, "data", None) not in operator_overlays]
            if state.deliberation_viewer_open:
                overlay.append(ft.Container(
                    ft.Column([
                        ft.Row([ft.Text("LIVE DELIBERATION", color=state.theme.primary_color,
                                        weight=ft.FontWeight.BOLD, expand=True),
                                ft.TextButton("CLOSE", on_click=close_deliberation,
                                              style=ft.ButtonStyle(color=state.theme.accent_color))]),
                        _register_live_panel(state, "deliberation_assessments", lambda: build_assessments(state)),
                    ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                    top=24, bottom=FOOTER_HEIGHT + 24, left=24, right=24, padding=16,
                    border=ft.border.all(2, state.theme.accent_color),
                    bgcolor=state.theme.surface_color, data="live_deliberation"))
            if state.directorate_boot_open:
                overlay.append(ft.Container(
                    _register_live_panel(state, "directorate_boot", lambda: build_boot(
                        state.theme, state.directorate, state.directorate_busy, retry_directorate,
                        continue_directorate, state.directorate_animation, state.reduced_motion,
                        change_animation, change_motion)),
                    top=24, bottom=FOOTER_HEIGHT + 24, left=24, right=24,
                    bgcolor=state.theme.background_color, data="directorate_boot"))
            if state.directorate_open:
                roll = _register_live_panel(state, "directorate_roll", lambda: build_dispatch_roll(
                    state.directorate, animation=state.directorate_animation, reduced_motion=state.reduced_motion))
                actions = _register_live_panel(state, "directorate_actions", lambda: build_dispatch_actions(
                    state.theme, state.directorate, copy_latest_dispatch, export_latest_dispatch, directorate_history))
                overlay.append(ft.Container(build_dispatch_desk(state.theme, state.directorate, roll,
                    close_directorate, copy_latest_dispatch, export_latest_dispatch, directorate_history, actions),
                    top=24, bottom=FOOTER_HEIGHT + 24, left=24, right=24,
                    bgcolor=state.theme.background_color, data="directorate_desk"))
            if state.diagnostics_drawer_open:
                overlay.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [ft.IconButton(
                                        icon=ft.Icons.CLOSE,
                                        icon_color=state.theme.accent_color,
                                        tooltip="Close diagnostics",
                                        on_click=close_diagnostics,
                                        data="close_diagnostics",
                                    )],
                                    alignment=ft.MainAxisAlignment.END,
                                ),
                                ft.Container(
                                    build_diagnostics_drawer(state, open_trace_viewer=open_trace_viewer,
                                                             open_system_checks=open_directorate_boot),
                                    expand=True,
                                ),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                        width=380,
                        top=8,
                        right=8,
                        bottom=FOOTER_HEIGHT + 8,
                        padding=10,
                        border=ft.border.all(1, state.theme.accent_color),
                        bgcolor=state.theme.surface_color,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        data="diagnostics_drawer",
                    )
                )
            if state.command_palette_open:
                overlay.append(
                    ft.Container(
                        content=build_command_palette(state, on_action=handle_command_action),
                        alignment=ft.alignment.center,
                        data="command_palette",
                    )
                )
            if state.trace_viewer_open:
                overlay.append(
                    ft.Container(
                        content=build_decision_trace_viewer(state, on_filter=handle_trace_filter),
                        alignment=ft.alignment.center_left,
                        padding=ft.padding.only(left=24),
                        data="decision_trace_viewer",
                    )
                )
            if state.proposal_history_open:
                overlay.append(
                    ft.Container(
                        content=build_proposal_history_viewer(state, on_action=handle_proposal_history_action),
                        alignment=ft.alignment.center,
                        data="proposal_history_viewer",
                    )
                )
            if state.visual_review_viewer_open:
                overlay.append(
                    ft.Container(
                        content=build_visual_review_status_viewer(state),
                        alignment=ft.alignment.center,
                        data="visual_review_status",
                    )
                )
            if state.telemetry_viewer_open:
                overlay.append(
                    ft.Container(
                        content=build_telemetry_snapshot_viewer(state),
                        alignment=ft.alignment.center,
                        data="telemetry_snapshot",
                    )
                )
            if state.simulation_viewer_open:
                overlay.append(
                    ft.Container(
                        content=build_simulation_viewer(state, on_action=handle_simulation_action),
                        alignment=ft.alignment.center,
                        data="simulation_viewer",
                    )
                )
            if state.simulation_create_open:
                overlay.append(
                    ft.Container(
                        content=build_simulation_create_overlay(state, on_create=handle_simulation_create),
                        alignment=ft.alignment.center,
                        data="simulation_create_overlay",
                    )
                )
            if state.branch_tree_viewer_open:
                overlay.append(
                    ft.Container(
                        content=build_branch_tree_viewer(
                            state,
                            on_expand=handle_branch_expand_request,
                            on_export=handle_simulation_export,
                        ),
                        alignment=ft.alignment.center,
                        data="branch_tree_viewer",
                    )
                )
            if state.simulation_branch_expand_open:
                overlay.append(
                    ft.Container(
                        content=build_branch_expand_overlay(state, on_expand=handle_branch_expand),
                        alignment=ft.alignment.center,
                        data="simulation_branch_expand_overlay",
                    )
                )
            if state.data_sources_viewer_open:
                overlay.append(
                    ft.Container(
                        content=build_data_sources_viewer(state),
                        alignment=ft.alignment.center,
                        data="data_sources_viewer",
                    )
                )
            # Transparent full-page overlay containers still take part in hit
            # testing. Keep every operator viewer above the command bar.
            for control in overlay:
                if getattr(control, "data", None) in operator_overlays:
                    if control.top is None:
                        control.top = 8
                    if control.bottom is None:
                        control.bottom = FOOTER_HEIGHT + 8
                    if control.left is None and control.right is None:
                        control.left = 8
                        control.right = 8
                    control.clip_behavior = ft.ClipBehavior.HARD_EDGE
        page.update()
    finally:
        state.render_in_progress = False


def _start_status_polling(page: ft.Page, state: GuiState, interval: float = GUI_ACTIVITY_REFRESH_INTERVAL_SECONDS) -> None:
    if state.ui_stopped.is_set():
        return
    def poll() -> None:
        last_status_refresh = time.monotonic()
        while not state.ui_stopped.wait(interval):
            try:
                advance_war_room_activity(state)
                now = time.monotonic()
                if not state.directorate_busy and now - last_status_refresh >= GUI_PROVIDER_REFRESH_INTERVAL_SECONDS:
                    refresh_gui_status(state)
                    last_status_refresh = now
                refresh_telemetry_for_gui(state)
                _refresh_live_page(page, state)
            except Exception as exc:
                log_error("gui_status_poll_error", exc)
                log_war_room_runtime("ui_refresh_error", {"error": str(exc)}, level="ERROR")

    page.run_thread(poll)
    page.run_thread(_poll_monolith_feedback, page, state)
    page.run_thread(_poll_directorate_roll, page, state)


def _poll_directorate_roll(page: ft.Page, state: GuiState) -> None:
    """Reveal new report lines without rebuilding the editor or other panels."""
    completed = None
    while not state.ui_stopped.wait(.2):
        if not state.directorate_open or state.reduced_motion or not state.directorate_animation:
            continue
        dispatches = state.directorate.dispatches()
        if not dispatches or dispatches[-1] is completed:
            continue
        latest = dispatches[-1]
        try:
            with state.render_lock:
                registered = state.live_panels.get("directorate_roll")
                if registered is None:
                    continue
                roll, builder = registered
                roll.controls = builder().controls
                page.update(roll)
                if time.monotonic() - latest.received_at >= 3:
                    completed = latest
        except Exception as exc:
            log_error("gui_directorate_reveal_error", exc)


def _poll_monolith_feedback(page: ft.Page, state: GuiState) -> None:
    """Update only the borders, preserving focus and the model turn lifecycle."""
    while not state.ui_stopped.wait(1.2):
        try:
            with state.render_lock:
                registered = state.live_panels.get("build_monolith_panel")
                if not registered:
                    continue
                panel = registered[0]
                changed = []
                for card in panel.controls[1:5]:
                    agent = card.data["agent_id"]
                    color, width = card_border(state.theme, state.monolith_statuses.get(agent, "ONLINE"),
                        state.monolith_feedback.get(agent), time.monotonic(),
                        reduced_motion=state.reduced_motion or not state.directorate_animation)
                    if card.border.top.color != color or card.border.top.width != width:
                        card.border = ft.border.all(width, color)
                        changed.append(card)
                if changed:
                    page.update(*changed)
        except Exception as exc:
            log_error("gui_monolith_feedback_error", exc)


def run_flet_gui(
    theme_key: str,
    config: RuntimeConfig,
    nodes: Dict[str, NodeIdentity] | None = None,
    compact_header: bool = True,
    window_mode: GuiWindowMode = "maximized",
    startup_config_error: bool = False,
    startup_config_path: Path | None = None,
    startup_config_loader: Callable[[], RuntimeConfig] | None = None,
) -> None:
    ensure_flet_desktop_runtime()
    state = create_gui_state(theme_key, config, nodes, compact_header=compact_header,
                             window_mode=window_mode, initialize=False)
    state.directorate_boot_open = startup_config_error
    state.directorate_config_failed = startup_config_error
    state.directorate_config_path = startup_config_path
    state.directorate_config_loader = startup_config_loader
    if startup_config_error:
        state.directorate.emit("CONFIG", "STARTUP_CHECK", "FAILED", "Configuration unreadable; correct it locally and retry", check=True)

    def target(page: ft.Page) -> None:
        if hasattr(page, "on_disconnect"):
            page.on_disconnect = lambda _: state.ui_stopped.set()
        state.directorate_busy = True
        try:
            _render_page(page, state)
        except Exception as exc:
            state.directorate_busy = False
            state.directorate.emit("INTERFACE", "STARTUP_CHECK", "FAILED",
                                  f"Interface mount failed ({type(exc).__name__}); correct local assets and retry", check=True)
            page.controls.clear()
            page.add(ft.Container(build_boot(state.theme, state.directorate, False,
                                            retry=lambda _: target(page), animation=False), expand=True, padding=24))
            page.update()
            return
        state.directorate.emit("INTERFACE", "STARTUP_CHECK", "AVAILABLE", "Flet interface mounted", check=True)
        marker = os.getenv("CONSENSUS_GUI_READY_MARKER")
        if marker:
            Path(marker).write_text("ready", encoding="utf-8")
        def initialize() -> None:
            initialize_directorate(state, lambda: _refresh_live_page(page, state))
            _start_status_polling(page, state)
        page.run_thread(initialize)

    ft.app(target=target)


__all__ = [
    "LEFT_COLUMN_FLEX",
    "CENTER_COLUMN_FLEX",
    "RIGHT_COLUMN_FLEX",
    "PROPOSAL_HEIGHT",
    "FOOTER_HEIGHT",
    "GuiState",
    "create_gui_state",
    "submit_proposal_for_gui",
    "set_aurelius_voice_loop",
    "refresh_gui_status",
    "refresh_bellator_intelligence_status",
    "refresh_bellator_intelligence_for_gui",
    "run_flet_gui",
    "ensure_flet_desktop_runtime",
    "build_gui_layout",
    "build_diagnostics_drawer",
    "build_command_palette",
    "build_decision_trace_viewer",
    "build_proposal_history_viewer",
    "build_simulation_viewer",
    "build_simulation_create_overlay",
    "build_branch_tree_viewer",
    "build_branch_expand_overlay",
    "build_data_sources_viewer",
    "execute_command_palette_action",
    "filter_decision_traces",
    "runtime_snapshot_from_gui_state",
    "set_diagnostics_drawer_open",
    "latest_verdict_text",
    "apply_gui_window_mode",
    "GUI_WINDOW_MODES",
    "COMMAND_PALETTE_ACTIONS",
    "GUI_ACTIVITY_REFRESH_INTERVAL_SECONDS",
    "GUI_PROVIDER_REFRESH_INTERVAL_SECONDS",
    "GUI_INTERACTION_HOLD_SECONDS",
    "HEARTBEAT_MESSAGES",
    "advance_gui_heartbeat",
    "advance_war_room_activity",
    "read_recent_log_events",
    "read_recent_decisions",
    "export_decision_history",
    "export_session_logs",
    "open_theme_preview_folder",
]
