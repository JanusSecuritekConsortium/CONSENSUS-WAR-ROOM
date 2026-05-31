from __future__ import annotations

import json
import os
import shutil
import subprocess
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
from core.decision_trace import list_recent_traces, read_latest_trace
from core.health import run_health_check
from core.intelligence.bellator_context_builder import (
    build_bellator_context_packet,
    build_bellator_diagnostics_payload,
)
from core.data_sources.enrichment import build_aeternum_data_enrichment
from core.data_sources.health import build_data_sources_status
from core.llm.prompts import build_node_prompt
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
    monolith_activity_phrase,
    phase_for_verdict,
    theme_reasoning_phrase,
)
from core.voting.engine import ConsensusEngine
from core.voting.parser import parse_vote
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
from ui.components.monolith_panel import build_monolith_panel
from ui.components.proposal_panel import build_proposal_panel
from ui.components.status_panel import build_status_panel
from ui.components.telemetry_panel import build_telemetry_panel, telemetry_graph_lines, telemetry_summary_lines
from ui.components.theme_switcher import build_theme_switcher
from ui.components.verdict_panel import build_verdict_panel
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


FOOTER_HEIGHT = 62
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

    @property
    def theme(self):
        return THEMES[self.theme_key]


def create_gui_state(
    theme_key: str,
    config: RuntimeConfig,
    nodes: Dict[str, NodeIdentity] | None = None,
    compact_header: bool = True,
    window_mode: GuiWindowMode = "maximized",
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
        aurelius_runtime=get_aurelius_runtime(),
    )
    refresh_gui_status(state)
    refresh_telemetry_for_gui(state)
    state.heartbeat_text = ambient_message(state.theme_key, state.pulse_index)
    state.timeline_events = [
        append_timeline([], "SYSTEM", f"{state.theme.display_name} interface online")[0]
    ]
    refresh_bellator_intelligence_status(state)
    log_war_room_runtime("gui_state_created", {"theme": state.theme_key, "window_mode": window_mode})
    return state


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
    policy = state.provider_status.get("fallback_policy", {}) if isinstance(state.provider_status, dict) else {}
    if _provider_is_degraded(state.provider_status) and runtime.fallback_enabled:
        return "PROVIDER DEGRADED - MOCK FALLBACK ACTIVE"
    if isinstance(policy, dict) and policy.get("mode") in {"degraded", "offline"} and policy.get("fallback_enabled"):
        return "PROVIDER DEGRADED - MOCK FALLBACK ACTIVE"
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
            "main_column_expand": [2, 6, 2],
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
            if value in {"THINKING", *VOTE_STATUS_VALUES}:
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
    state.pulse_index += 1
    state.cursor_visible = cursor_frame(state.pulse_index) == "_"
    state.heartbeat_text = ambient_message(state.theme_key, state.pulse_index)
    state.monolith_latencies_ms = {
        agent_id: default_latencies(state.pulse_index)[agent_id]
        for agent_id in state.monolith_activity_states
    }
    if state.pulse_index % 8 == 0:
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
        "vote": vote.vote.value,
        "confidence": vote.confidence,
        "evidence_quality": vote.evidence_quality,
        "critical_risk": vote.critical_risk,
        "critical_domain_relevance": vote.critical_domain_relevance,
        "validation_errors": list(vote.validation_errors),
        "reasoning": vote.reasoning,
        "response_time": vote.response_time,
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
    state.current_proposal = clean_proposal
    state.proposal_input_text = clean_proposal
    state.current_result = None
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
    session_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    memory_context = build_context_packet(clean_proposal)
    _set_lifecycle(state, LIFECYCLE_DISPATCHING, on_update)
    state.prior_decisions_used = int(memory_context.get("prior_decisions_used", 0) or 0)
    state.context_retrieval_status = context_status(memory_context)
    state.context_summary = str(memory_context.get("summary", "No prior decisions retrieved."))
    context: Dict[str, object] = {"session_id": session_id, "theme": state.theme_key, "memory_context": memory_context}
    votes: Dict[str, Vote] = {}
    state.monolith_statuses = {
        **{key: "THINKING" for key in TRIBUNAL_AGENT_IDS},
        ARBITER: "ONLINE" if state.provider_status.get("status") == "ready" else "DEGRADED",
    }
    for agent_id in TRIBUNAL_AGENT_IDS:
        transition_state(
            state.monolith_activity_states,
            agent_id,
            "THINKING",
            state.timeline_events,
            "loaded vote package",
        )
    _set_lifecycle(state, LIFECYCLE_ANALYZING, on_update)
    log_event(
        "proposal",
        {"session_id": session_id, "theme": state.theme_key, "sequential": state.config.sequential, "query": clean_proposal},
    )

    try:
        for agent_id in TRIBUNAL_AGENT_IDS:
            state.monolith_statuses[agent_id] = "THINKING"
            transition_state(
                state.monolith_activity_states,
                agent_id,
                "ANALYZING",
                state.timeline_events,
                monolith_activity_phrase(agent_id, len(votes)),
            )
            _notify(on_update)
            node = state.nodes[agent_id]
            runtime_context = context if state.config.sequential else {
                "session_id": session_id,
                "theme": state.theme_key,
                "memory_context": memory_context,
            }
            if agent_id == BELLATOR:
                runtime_context = dict(runtime_context)
            runtime_context["model"] = node.model
            if agent_id == BELLATOR:
                packet = build_bellator_context_packet(clean_proposal)
                runtime_context["bellator_context_packet"] = packet
                state.bellator_intelligence_diagnostics = build_bellator_diagnostics_payload(packet)
            if agent_id == AETERNUM:
                runtime_context["aeternum_data_packet"] = build_aeternum_data_enrichment(clean_proposal, live=False)
            prompt = build_node_prompt(node, clean_proposal, runtime_context)
            vote_started = time.perf_counter()
            try:
                transition_state(
                    state.monolith_activity_states,
                    agent_id,
                    "VOTING",
                    state.timeline_events,
                    "casting tribunal vote",
                )
                raw = runtime.send_to_agent(agent_id, prompt, runtime_context)
                elapsed = time.perf_counter() - vote_started
                vote = parse_vote(raw, node, elapsed, "msty-runtime")
                vote.node_key = agent_id
            except Exception as exc:
                elapsed = time.perf_counter() - vote_started
                log_error("vote_error", exc, {"session_id": session_id, "agent_id": agent_id, "model": node.model, "elapsed": elapsed})
                vote = Vote(
                    node_key=agent_id,
                    role=node.role,
                    vote=VoteValue.ABSTAIN,
                    confidence=0.0,
                    reasoning=f"Runtime failure: {exc}",
                    evidence_quality=0.0,
                    critical_risk=False,
                    validation_errors=[f"runtime_failure:{exc.__class__.__name__}"],
                    model=node.model,
                    response_time=elapsed,
                )
            votes[agent_id] = vote
            state.convergence_percent = convergence_percent(votes)
            append_reasoning_event(
                state.reasoning_stream,
                f"{agent_id} vote registered; convergence {state.convergence_percent:.0%}",
            )
            state.monolith_statuses[agent_id] = vote.vote.value
            state.monolith_vote_details[agent_id] = _vote_detail(vote)
            state.monolith_activity_states[agent_id] = "ERROR" if vote.validation_errors else "IDLE"
            append_timeline(state.timeline_events, agent_id, f"vote {vote.vote.value.lower()} confidence {vote.confidence:.0%}")
            log_event(
                "vote",
                {
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "vote": vote.vote.value,
                    "confidence": vote.confidence,
                    "evidence_quality": vote.evidence_quality,
                    "critical_risk": vote.critical_risk,
                    "validation_errors": vote.validation_errors,
                    "model": vote.model,
                    "response_time": vote.response_time,
                },
                level="ERROR" if vote.validation_errors else "INFO",
            )
            if state.config.sequential:
                context[agent_id] = {
                    "vote": vote.vote.value,
                    "confidence": vote.confidence,
                    "reasoning": vote.reasoning,
                }
            state.logs = read_recent_log_events()
            _notify(on_update)

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
        terminal_phase = phase_for_verdict(result.verdict, result.terminal_branch, result.review_triggers)
        _set_lifecycle(state, terminal_phase, on_update)
        state.current_result = result
        state.monolith_statuses[ARBITER] = result.verdict.value
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
        )
        state.displayed_synthesis = result.reason
        state.consensus_locked = True
        state.monolith_activity_states[ARBITER] = "IDLE"
        append_timeline(state.timeline_events, ARBITER, "consensus locked")
        setattr(result, "lifecycle_events", list(state.lifecycle_events))
        setattr(result, "phase_durations", dict(state.phase_durations))
        setattr(result, "reasoning_stream", list(state.reasoning_stream))
        setattr(result, "convergence_percent", state.convergence_percent)
        record_result(result)
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
        except Exception as exc:
            log_event("gui_session_memory_write_failed", {"session_id": result.session_id, "error": str(exc)}, level="WARN")
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
    except Exception:
        _set_lifecycle(state, LIFECYCLE_ERROR_DEGRADED, None)
        for agent_id in [*TRIBUNAL_AGENT_IDS, ARBITER]:
            state.monolith_activity_states[agent_id] = "ERROR"
        append_timeline(state.timeline_events, "ERROR", "proposal lifecycle degraded")
        log_war_room_runtime("proposal_lifecycle_error", {"theme": state.theme_key}, level="ERROR")
        state.provider_warning = state.provider_warning or "PROVIDER DEGRADED - MOCK FALLBACK ACTIVE"
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
    path = Path("_ARBITER") / "theme_previews"
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.startfile(path)  # type: ignore[attr-defined]
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

    shortcut_text = "Ctrl+K Command   Ctrl+D Diagnostics   Ctrl+T Theme   Ctrl+H History   Ctrl+E Export"
    footer_shortcuts = ft.Container(
        content=ft.Text(
            shortcut_text,
            color=theme.secondary_text or theme.secondary_color,
            size=10,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            text_align=ft.TextAlign.CENTER,
            data="footer_shortcuts_text",
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
                width=230,
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
                width=230,
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
            build_monolith_panel(
                theme,
                state.nodes,
                state.monolith_statuses,
                vote_details=state.monolith_vote_details,
                memory_status=state.memory_status,
                provider_status=str(state.provider_status.get("status", "unknown")),
                last_verdict=last_verdict,
                session_id=session_id,
                lifecycle_state=state.lifecycle_state,
                runtime_details=build_runtime_details(
                    state.monolith_activity_states,
                    state.monolith_latencies_ms,
                    state.pulse_index,
                ),
        ),
        expand=2,
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
                    ),
                    expand=4,
                    height=layout_meta.proposal_panel_min_height,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    data={"role": "proposal_panel_region"},
                ),
                ft.Container(
                    build_verdict_panel(
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
                    ),
                    expand=6,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    data={"role": "verdict_panel_region"},
                ),
            ],
            spacing=layout_meta.proposal_verdict_gap,
            expand=True,
        ),
        expand=6,
    )
    right = ft.Container(
        ft.Column(
            [
                ft.Container(
                    ft.Column(
                        [
                            build_status_panel(
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
                            ),
                        ],
                        spacing=8,
                        tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
                build_log_panel(
                    theme,
                    state.logs,
                    state.recent_decisions,
                    timeline_events=state.timeline_events,
                    bellator_intelligence=state.bellator_intelligence_diagnostics,
                    refresh_bellator_intelligence=refresh_bellator_intelligence,
                ),
            ],
            spacing=12,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        expand=2,
    )
    body = ft.Row(
        [left, center, right],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        spacing=10,
        expand=True,
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
                build_header(
                    theme,
                    str(state.provider_status.get("status", "unknown")),
                    state.memory_status,
                    state.current_result.session_id if state.current_result else "--",
                    compact=state.compact_header,
                    ambient_status=state.heartbeat_text,
                    health_badge=state.runtime_snapshot_cache.get("health_badge"),
                    telemetry=state.telemetry_snapshot,
                ),
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
    shell.decision_trace_viewer = build_decision_trace_viewer(state)  # type: ignore[attr-defined]
    shell.proposal_history_viewer = build_proposal_history_viewer(state)  # type: ignore[attr-defined]
    shell.visual_review_status_viewer = build_visual_review_status_viewer(state)  # type: ignore[attr-defined]
    shell.telemetry_snapshot_viewer = build_telemetry_snapshot_viewer(state)  # type: ignore[attr-defined]
    shell.simulation_viewer = build_simulation_viewer(state)  # type: ignore[attr-defined]
    shell.simulation_create_overlay = build_simulation_create_overlay(state)  # type: ignore[attr-defined]
    shell.branch_tree_viewer = build_branch_tree_viewer(state)  # type: ignore[attr-defined]
    return shell


def build_diagnostics_drawer(state: GuiState, open_trace_viewer=None) -> ft.Control:
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
    if state.render_in_progress:
        log_war_room_runtime("ui_render_skipped_reentrant", {"theme": state.theme_key}, level="WARN")
        return
    state.render_in_progress = True
    try:
        _apply_page_theme(page, state)
        apply_gui_window_mode(page, state.window_mode)

        def submit(proposal: str) -> None:
            def worker() -> None:
                def update() -> None:
                    _render_page(page, state)

                try:
                    submit_proposal_live_for_gui(state, proposal, on_update=update)
                except Exception as exc:
                    log_error("gui_submission_error", exc, {"theme": state.theme_key})
                    state.logs = [f"ERROR gui_submission_error: {exc}", *state.logs[:10]]
                _render_page(page, state)

            page.run_thread(worker)

        def switch_theme(next_theme: str) -> None:
            resolved = resolve_theme_key(next_theme)
            if resolved in THEMES:
                state.theme_key = resolved
                state.config.theme = resolved
                state.heartbeat_text = ambient_message(state.theme_key, state.pulse_index)
                append_timeline(state.timeline_events, "SYSTEM", f"theme switched to {state.theme.display_name}")
                refresh_gui_status(state)
                _render_page(page, state)

        def refresh(_: ft.ControlEvent | None = None) -> None:
            refresh_gui_status(state)
            _render_page(page, state)

        def recheck_provider(_: ft.ControlEvent | None = None) -> None:
            recheck_provider_for_gui(state)
            _render_page(page, state)

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

        def on_keyboard_event(event) -> None:
            key = str(getattr(event, "key", "") or "").upper()
            ctrl = bool(getattr(event, "ctrl", False) or getattr(event, "meta", False))
            if ctrl and key == "K":
                state.command_palette_open = not state.command_palette_open
                log_event(
                    "gui_command_palette",
                    {"open": state.command_palette_open, "theme": state.theme_key},
                )
                _render_page(page, state)
            elif ctrl and key == "D":
                toggle_diagnostics(None)
            elif ctrl and key == "T":
                execute_command_palette_action(state, "Toggle Theme")
                _render_page(page, state)
            elif ctrl and key == "H":
                state.proposal_history_open = not state.proposal_history_open
                _render_page(page, state)
            elif ctrl and key == "E":
                try:
                    execute_command_palette_action(state, "Export Latest Verdict")
                except Exception:
                    pass
                _render_page(page, state)

        if hasattr(page, "on_keyboard_event"):
            page.on_keyboard_event = on_keyboard_event

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
            }
            overlay[:] = [control for control in overlay if getattr(control, "data", None) not in operator_overlays]
            if state.diagnostics_drawer_open:
                overlay.append(
                    ft.Container(
                        content=ft.Container(
                            build_diagnostics_drawer(state),
                            width=380,
                            padding=10,
                            border=ft.border.all(1, state.theme.accent_color),
                            bgcolor=state.theme.surface_color,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        ),
                        alignment=ft.alignment.center_right,
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
        page.update()
    finally:
        state.render_in_progress = False


def _start_status_polling(page: ft.Page, state: GuiState, interval: float = GUI_ACTIVITY_REFRESH_INTERVAL_SECONDS) -> None:
    def poll() -> None:
        last_status_refresh = time.monotonic()
        while True:
            time.sleep(interval)
            try:
                advance_war_room_activity(state)
                now = time.monotonic()
                if now < state.ui_interaction_hold_until:
                    continue
                if now - last_status_refresh >= GUI_PROVIDER_REFRESH_INTERVAL_SECONDS:
                    refresh_gui_status(state)
                    last_status_refresh = now
                refresh_telemetry_for_gui(state)
                _render_page(page, state)
            except Exception as exc:
                log_error("gui_status_poll_error", exc)
                log_war_room_runtime("ui_refresh_error", {"error": str(exc)}, level="ERROR")

    page.run_thread(poll)


def run_flet_gui(
    theme_key: str,
    config: RuntimeConfig,
    nodes: Dict[str, NodeIdentity] | None = None,
    compact_header: bool = True,
    window_mode: GuiWindowMode = "maximized",
) -> None:
    ensure_flet_desktop_runtime()
    state = create_gui_state(theme_key, config, nodes, compact_header=compact_header, window_mode=window_mode)

    def target(page: ft.Page) -> None:
        _render_page(page, state)
        marker = os.getenv("CONSENSUS_GUI_READY_MARKER")
        if marker:
            Path(marker).write_text("ready", encoding="utf-8")
        _start_status_polling(page, state)

    ft.app(target=target)


__all__ = [
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
