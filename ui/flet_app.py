from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Literal

import flet as ft

from assistant.aurelius_runtime import AureliusRuntime, get_aurelius_runtime
from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import RuntimeConfig
from core.history import record_result
from core.health import run_health_check
from core.llm.prompts import build_node_prompt
from core.logging import log_error, log_event
from core.memory.context import build_context_packet, context_status
from core.memory.session import upsert_session_record
from core.models import NodeIdentity, TribunalResult, Vote, VoteValue
from core.paths import EXPORT_DIR, HISTORY_PATH, SYSTEM_LOG_PATH
from core.tribunal import Tribunal
from core.voting.engine import ConsensusEngine
from core.voting.parser import parse_vote
from core.voting.rules import ConsensusRules
from integrations.msty.runtime import MstyRuntime
from ui.animations.typewriter import reveal_text_with_cursor_sync
from ui.components.header import build_header
from ui.components.log_panel import build_log_panel
from ui.components.monolith_panel import build_monolith_panel
from ui.components.proposal_panel import build_proposal_panel
from ui.components.status_panel import build_status_panel
from ui.components.theme_switcher import build_theme_switcher
from ui.components.verdict_panel import build_verdict_panel
from ui.themes.catalog import THEMES, resolve_theme_key
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
LIFECYCLE_PROPOSAL_RECEIVED = "PROPOSAL RECEIVED"
LIFECYCLE_DELIBERATING = "MONOLITHS DELIBERATING"
LIFECYCLE_VOTES_RECEIVED = "VOTES RECEIVED"
LIFECYCLE_SYNTHESIZING = "ARBITER SYNTHESIZING"
LIFECYCLE_VERDICT_ISSUED = "VERDICT ISSUED"
LIFECYCLE_ERROR_DEGRADED = "ERROR / DEGRADED"
LIFECYCLE_STATES = (
    LIFECYCLE_IDLE,
    LIFECYCLE_PROPOSAL_RECEIVED,
    LIFECYCLE_DELIBERATING,
    LIFECYCLE_VOTES_RECEIVED,
    LIFECYCLE_SYNTHESIZING,
    LIFECYCLE_VERDICT_ISSUED,
    LIFECYCLE_ERROR_DEGRADED,
)
VOTE_STATUS_VALUES = {value.value for value in VoteValue}
GuiUpdateCallback = Callable[[], None]
HEARTBEAT_MESSAGES = (
    "MONOLITH LINK STABLE",
    "MEMORY INDEX READY",
    "PROVIDER CHECK PENDING",
    "TRIBUNAL IDLE",
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
    monolith_activity_states: Dict[str, str] = field(default_factory=default_activity_states)
    monolith_latencies_ms: Dict[str, int] = field(default_factory=default_latencies)
    proposal_file_mtime: float | None = None
    ui_interaction_hold_until: float = 0.0

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
    state.heartbeat_text = ambient_message(state.theme_key, state.pulse_index)
    state.timeline_events = [
        append_timeline([], "SYSTEM", f"{state.theme.display_name} interface online")[0]
    ]
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
    state.logs = read_recent_log_events()
    state.recent_decisions = read_recent_decisions()


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
        "reasoning": vote.reasoning,
        "response_time": vote.response_time,
    }


def _set_lifecycle(state: GuiState, lifecycle_state: str, on_update: GuiUpdateCallback | None = None) -> None:
    state.lifecycle_state = lifecycle_state
    append_timeline(state.timeline_events, "LIFECYCLE", lifecycle_state.lower())
    log_war_room_runtime("proposal_lifecycle", {"state": lifecycle_state, "theme": state.theme_key})
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
    state.current_result = None
    state.monolith_vote_details = {}
    state.displayed_synthesis = ""
    state.displayed_confidence = 0.0
    state.provider_warning = ""
    state.consensus_locked = False
    for agent_id in [*TRIBUNAL_AGENT_IDS, ARBITER]:
        state.monolith_activity_states[agent_id] = "IDLE"
    _set_lifecycle(state, LIFECYCLE_PROPOSAL_RECEIVED, on_update)
    append_timeline(state.timeline_events, "PROPOSAL", "received vote package")
    log_event("gui_proposal_submitted", {"theme": state.theme_key, "query": clean_proposal})
    log_war_room_runtime("proposal_received", {"theme": state.theme_key, "query": clean_proposal})
    runtime = MstyRuntime(state.config)
    state.provider_warning = _fallback_warning(state, runtime)
    rules = ConsensusRules(
        minimum_confidence=state.config.minimum_confidence,
        quorum=state.config.quorum,
        majority=state.config.majority,
        high_risk_review=state.config.high_risk_review,
    )
    session_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    memory_context = build_context_packet(clean_proposal)
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
    _set_lifecycle(state, LIFECYCLE_DELIBERATING, on_update)
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
                "analyzing proposal context",
            )
            _notify(on_update)
            node = state.nodes[agent_id]
            runtime_context = context if state.config.sequential else {
                "session_id": session_id,
                "theme": state.theme_key,
                "memory_context": memory_context,
            }
            runtime_context["model"] = node.model
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
                    vote=VoteValue.ERROR,
                    confidence=0.0,
                    reasoning=f"Runtime failure: {exc}",
                    model=node.model,
                    response_time=elapsed,
                )
            votes[agent_id] = vote
            state.monolith_statuses[agent_id] = vote.vote.value
            state.monolith_vote_details[agent_id] = _vote_detail(vote)
            state.monolith_activity_states[agent_id] = "ERROR" if vote.vote == VoteValue.ERROR else "IDLE"
            append_timeline(state.timeline_events, agent_id, f"vote {vote.vote.value.lower()} confidence {vote.confidence:.0%}")
            log_event(
                "vote",
                {
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "vote": vote.vote.value,
                    "confidence": vote.confidence,
                    "model": vote.model,
                    "response_time": vote.response_time,
                },
                level="ERROR" if vote.vote == VoteValue.ERROR else "INFO",
            )
            if state.config.sequential:
                context[agent_id] = {
                    "vote": vote.vote.value,
                    "confidence": vote.confidence,
                    "reasoning": vote.reasoning,
                }
            state.logs = read_recent_log_events()
            _notify(on_update)

        _set_lifecycle(state, LIFECYCLE_VOTES_RECEIVED, on_update)
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
        record_result(result)
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
                            "reasoning": vote.reasoning,
                            "model": vote.model,
                            "response_time": vote.response_time,
                        }
                        for agent_id, vote in result.votes.items()
                    },
                    "arbiter_verdict": result.verdict.value,
                    "verdict": result.verdict.value,
                    "synthesis_summary": result.reason,
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
                "elapsed": round(time.perf_counter() - started, 6),
            },
        )
        _set_lifecycle(state, LIFECYCLE_VERDICT_ISSUED, on_update)
        state.logs = read_recent_log_events()
        state.recent_decisions = read_recent_decisions()
        log_event("gui_verdict_update", {"session_id": result.session_id, "verdict": result.verdict.value})
        return result
    except Exception:
        state.lifecycle_state = LIFECYCLE_ERROR_DEGRADED
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


def build_gui_layout(
    state: GuiState,
    submit,
    switch_theme,
    refresh,
    run_health,
    close_gui,
    recheck_provider=None,
    toggle_aurelius_voice=None,
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

    footer_controls = ft.Row(
        [
            build_theme_switcher(theme, switch_theme, on_interaction=hold_footer_interaction),
            ft.Switch(
                label="AURELIUS Voice Loop",
                value=state.aurelius_voice_loop_enabled,
                on_change=toggle_aurelius_voice,
                active_color=theme.accent_color,
            ),
            terminal_button("EXPORT HISTORY", lambda _: export_decision_history()),
            terminal_button("EXPORT LOGS", lambda _: export_session_logs()),
            terminal_button("OPEN PREVIEWS", lambda _: open_theme_preview_folder()),
            terminal_button("REFRESH STATUS", refresh),
            terminal_button("RECHECK PROVIDER", recheck_provider or refresh),
            terminal_button("HEALTH CHECK", run_health),
            terminal_button("SHUTDOWN GUI", close_gui),
        ],
        wrap=True,
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    last_verdict = state.current_result.verdict.value if state.current_result else "--"
    session_id = state.current_result.session_id if state.current_result else "--"
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
                ft.Container(build_proposal_panel(theme, submit), expand=3, clip_behavior=ft.ClipBehavior.HARD_EDGE),
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
                    ),
                    expand=7,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
            ],
            spacing=12,
            expand=True,
        ),
        expand=6,
    )
    right = ft.Container(
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
                build_log_panel(theme, state.logs, state.recent_decisions, timeline_events=state.timeline_events),
            ],
            spacing=12,
            expand=True,
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
    return ft.Container(
        content=ft.Column(
            [
                build_header(
                    theme,
                    str(state.provider_status.get("status", "unknown")),
                    state.memory_status,
                    state.current_result.session_id if state.current_result else "--",
                    compact=state.compact_header,
                    ambient_status=state.heartbeat_text,
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


def _render_page(page: ft.Page, state: GuiState) -> None:
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

    def toggle_aurelius_voice(event: ft.ControlEvent) -> None:
        set_aurelius_voice_loop(state, bool(event.control.value))
        _render_page(page, state)

    def run_health(_: ft.ControlEvent | None = None) -> None:
        report = run_health_check()
        state.logs = [f"HEALTH {report['status'].upper()}", *state.logs[:10]]
        _render_page(page, state)

    page.controls.clear()
    page.add(
        build_gui_layout(
            state,
            submit,
            switch_theme,
            refresh,
            run_health,
            lambda _: page.close(),
            recheck_provider=recheck_provider,
            toggle_aurelius_voice=toggle_aurelius_voice,
        )
    )
    page.update()


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
    state = create_gui_state(theme_key, config, nodes, compact_header=compact_header, window_mode=window_mode)

    def target(page: ft.Page) -> None:
        _render_page(page, state)
        _start_status_polling(page, state)

    ft.app(target=target)


__all__ = [
    "GuiState",
    "create_gui_state",
    "submit_proposal_for_gui",
    "set_aurelius_voice_loop",
    "refresh_gui_status",
    "run_flet_gui",
    "build_gui_layout",
    "apply_gui_window_mode",
    "GUI_WINDOW_MODES",
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
