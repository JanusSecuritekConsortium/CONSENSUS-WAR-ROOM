from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from core.paths import ARBITER_DIR, WAR_ROOM_RUNTIME_LOG_PATH


MONOLITH_ACTIVITY_STATES = (
    "IDLE",
    "THINKING",
    "ANALYZING",
    "VOTING",
    "SYNCHRONIZING",
    "ERROR",
    "OFFLINE",
)
PULSE_FRAMES = ("░", "▒", "▓", "▒")
CURSOR_FRAMES = ("_", " ")
WAR_ROOM_TIMELINE_LIMIT = 40
ACTIVE_MONOLITH_STATES = {"THINKING", "ANALYZING", "VOTING", "SYNCHRONIZING"}
PROPOSAL_LIFECYCLE_FLOW = (
    "PROPOSAL RECEIVED",
    "MONOLITH ACTIVATION",
    "VOTE SYNCHRONIZATION",
    "ARBITER SYNCHRONIZATION",
    "CONSENSUS LOCKED",
)
LIFECYCLE_HOOKS = (
    "on_proposal_received",
    "on_vote_received",
    "on_consensus_locked",
    "on_error",
)

MONOLITH_GLYPHS = {
    "RATIONALIS": "◇",
    "AETERNUM": "△",
    "BELLATOR": "▣",
    "ARBITER": "◆",
}

MONOLITH_IDLE_MESSAGES = {
    "RATIONALIS": (
        "PARSING LOGIC TREE",
        "CONSISTENCY MATRIX STABLE",
        "PROOF CHANNEL IDLE",
    ),
    "AETERNUM": (
        "FORECAST VECTOR STABLE",
        "MACRO TREND ANALYSIS READY",
        "TEMPORAL WINDOW QUIET",
    ),
    "BELLATOR": (
        "TACTICAL GRID SYNCHRONIZED",
        "THREAT MATRIX CLEAR",
        "ENGAGEMENT MODEL READY",
    ),
    "ARBITER": (
        "CONSENSUS CHANNEL IDLE",
        "VERDICT LOCK STANDBY",
        "TRIBUNAL VECTOR QUIET",
    ),
}


THEME_AMBIENT_MESSAGES = {
    "military": (
        "TACTICAL GRID SYNCHRONIZED",
        "NO ACTIVE THREATS DETECTED",
        "MONOLITH LINK STABLE",
        "EXCOMM CHANNEL READY",
    ),
    "eva": (
        "MAGI HARMONIZATION STABLE",
        "CASPER NODE STANDBY",
        "CENTRAL DOGMA LINK QUIET",
        "PATTERN ANALYSIS IDLE",
    ),
    "nerv": (
        "MAGI HARMONIZATION STABLE",
        "CASPER NODE STANDBY",
        "CENTRAL DOGMA LINK QUIET",
        "PATTERN ANALYSIS IDLE",
    ),
    "wh40k": (
        "COGITATOR LINK PURIFIED",
        "NOOSPHERIC FLOW STABLE",
        "MACHINE SPIRIT PLACATED",
        "DATA-VAULT RITE COMPLETE",
    ),
    "helldivers": (
        "DEMOCRATIC AUTHORIZATION STANDBY",
        "LIBERTY LOGIC STABLE",
        "STRATAGEM SAFETY GREEN",
        "SUPER EARTH SIGNAL CLEAN",
    ),
    "arasaka": (
        "EXECUTIVE OVERSIGHT ACTIVE",
        "CORPORATE NETWORK SYNCHRONIZED",
        "COUNTERINTELLIGENCE GRID IDLE",
        "BOARD VERDICT CHANNEL READY",
    ),
    "janus": (
        "DUAL CHANNEL STABLE",
        "ANALYTIC MIRROR ONLINE",
        "COUNTERPART SYNC QUIET",
        "REVERSIBILITY CHECK IDLE",
    ),
}


@dataclass(frozen=True)
class TimelineEvent:
    timestamp: str
    actor: str
    message: str

    def render(self) -> str:
        return f"[{self.timestamp}] {self.actor} {self.message}"


def default_activity_states() -> Dict[str, str]:
    return {**{agent_id: "IDLE" for agent_id in TRIBUNAL_AGENT_IDS}, ARBITER: "IDLE"}


def default_latencies(seed: int = 0) -> Dict[str, int]:
    keys = [*TRIBUNAL_AGENT_IDS, ARBITER]
    return {key: synthetic_latency_ms(key, seed) for key in keys}


def pulse_frame(index: int) -> str:
    return PULSE_FRAMES[index % len(PULSE_FRAMES)]


def monolith_pulse_frame(agent_id: str, state: str, index: int) -> str:
    cadence = {"RATIONALIS": 1, "AETERNUM": 2, "BELLATOR": 3, "ARBITER": 2}.get(agent_id, 1)
    frame = pulse_frame(index // cadence)
    if state.upper() in ACTIVE_MONOLITH_STATES:
        return frame * 2
    return frame


def cursor_frame(index: int) -> str:
    return CURSOR_FRAMES[index % len(CURSOR_FRAMES)]


def idle_activity_text(index: int) -> str:
    dots = "." * ((index % 3) + 1)
    return f"AWAITING PROPOSAL{dots}"


def monolith_idle_phrase(agent_id: str, index: int) -> str:
    phrases = MONOLITH_IDLE_MESSAGES.get(agent_id, ("AWAITING PROPOSAL",))
    phrase = phrases[(index // 5) % len(phrases)]
    return f"AWAITING PROPOSAL / {phrase}"


def ambient_messages_for_theme(theme_key: str) -> tuple[str, ...]:
    return THEME_AMBIENT_MESSAGES.get(theme_key.lower(), THEME_AMBIENT_MESSAGES["military"])


def ambient_message(theme_key: str, index: int) -> str:
    messages = ambient_messages_for_theme(theme_key)
    return messages[(index // 4) % len(messages)]


def synthetic_latency_ms(agent_id: str, pulse_index: int) -> int:
    base = 180 + (sum(ord(char) for char in agent_id) % 220)
    wobble = ((pulse_index * 37) + len(agent_id) * 19) % 170
    return base + wobble


def signal_bars(latency_ms: int) -> str:
    if latency_ms < 350:
        return "▮▮▮▮"
    if latency_ms < 650:
        return "▮▮▮▯"
    if latency_ms < 1100:
        return "▮▮▯▯"
    return "▮▯▯▯"


def timeline_event(actor: str, message: str, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%H:%M:%S")
    return TimelineEvent(timestamp, actor, message).render()


def append_timeline(events: List[str], actor: str, message: str, limit: int = WAR_ROOM_TIMELINE_LIMIT) -> List[str]:
    events.append(timeline_event(actor, message))
    if len(events) > limit:
        del events[: len(events) - limit]
    return events


def proposal_lifecycle_events() -> tuple[str, ...]:
    return PROPOSAL_LIFECYCLE_FLOW


def lifecycle_hook_names() -> tuple[str, ...]:
    return LIFECYCLE_HOOKS


def lifecycle_banner_label(lifecycle_state: str, consensus_locked: bool = False) -> str:
    normalized = lifecycle_state.upper()
    if consensus_locked and normalized == "EXPORT_READY":
        return "[CONSENSUS LOCKED]"
    if "CLASSIFYING" in normalized:
        return "[CLASSIFYING PROPOSAL]"
    if "DISPATCHING" in normalized:
        return "[DISPATCHING MONOLITHS]"
    if "ANALYZING" in normalized:
        return "[MONOLITH ANALYSIS]"
    if "DELIBERATING" in normalized:
        return "[MONOLITH DELIBERATION]"
    if "SYNTHESIZING" in normalized:
        return "[CONSENSUS SYNCHRONIZING]"
    if "CONSENSUS_REACHED" in normalized:
        return "[CONSENSUS LOCKED]"
    if "NO_CONSENSUS" in normalized:
        return "[NO CONSENSUS]"
    if "ESCALATION_REQUIRED" in normalized:
        return "[ESCALATION REQUIRED]"
    if "EXPORT_READY" in normalized:
        return "[EXPORT READY]"
    return "[IDLE]"


def build_runtime_details(
    states: Dict[str, str],
    latencies_ms: Dict[str, int],
    pulse_index: int,
) -> Dict[str, Dict[str, object]]:
    details: Dict[str, Dict[str, object]] = {}
    for agent_id, state in states.items():
        latency = latencies_ms.get(agent_id, synthetic_latency_ms(agent_id, pulse_index))
        state_name = state.upper()
        activity = monolith_idle_phrase(agent_id, pulse_index) if state_name == "IDLE" else state_name
        details[agent_id] = {
            "state": state,
            "glyph": MONOLITH_GLYPHS.get(agent_id, "*"),
            "pulse": monolith_pulse_frame(agent_id, state_name, pulse_index),
            "latency_ms": latency,
            "signal": signal_bars(latency),
            "activity": activity,
            "active": state_name in ACTIVE_MONOLITH_STATES,
        }
    return details


def log_war_room_runtime(event_type: str, payload: Dict[str, object] | None = None, level: str = "INFO") -> None:
    WAR_ROOM_RUNTIME_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "level": level.upper(),
        "event_type": event_type,
        "payload": payload or {},
    }
    with WAR_ROOM_RUNTIME_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def detect_proposal_file_change(last_mtime: float | None, path: Path | None = None) -> tuple[bool, float | None]:
    proposal_path = path or (ARBITER_DIR / "proposal.json")
    if not proposal_path.exists():
        return False, last_mtime
    current = proposal_path.stat().st_mtime
    if last_mtime is None:
        return False, current
    return current > last_mtime, current


def transition_state(
    states: Dict[str, str],
    agent_id: str,
    next_state: str,
    timeline: List[str] | None = None,
    message: str | None = None,
) -> None:
    normalized = next_state.upper()
    if normalized not in MONOLITH_ACTIVITY_STATES:
        raise ValueError(f"Unknown monolith activity state: {next_state}")
    states[agent_id] = normalized
    if timeline is not None:
        append_timeline(timeline, agent_id, message or f"state {normalized.lower()}")
    log_war_room_runtime(
        "monolith_state_transition",
        {"agent_id": agent_id, "state": normalized, "message": message or ""},
    )


def bounded_history(items: Iterable[str], limit: int = WAR_ROOM_TIMELINE_LIMIT) -> List[str]:
    history = list(items)
    return history[-limit:]


__all__ = [
    "MONOLITH_ACTIVITY_STATES",
    "ACTIVE_MONOLITH_STATES",
    "PULSE_FRAMES",
    "WAR_ROOM_TIMELINE_LIMIT",
    "THEME_AMBIENT_MESSAGES",
    "MONOLITH_GLYPHS",
    "MONOLITH_IDLE_MESSAGES",
    "ambient_message",
    "ambient_messages_for_theme",
    "append_timeline",
    "bounded_history",
    "build_runtime_details",
    "cursor_frame",
    "default_activity_states",
    "default_latencies",
    "detect_proposal_file_change",
    "idle_activity_text",
    "lifecycle_banner_label",
    "lifecycle_hook_names",
    "log_war_room_runtime",
    "monolith_idle_phrase",
    "monolith_pulse_frame",
    "proposal_lifecycle_events",
    "pulse_frame",
    "signal_bars",
    "synthetic_latency_ms",
    "timeline_event",
    "transition_state",
]
