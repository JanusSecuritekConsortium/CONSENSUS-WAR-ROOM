from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List

from core.models import FinalVerdict, Vote


TRIBUNAL_PHASES = (
    "IDLE",
    "CLASSIFYING",
    "DISPATCHING",
    "ANALYZING",
    "DELIBERATING",
    "SYNTHESIZING",
    "CONSENSUS_REACHED",
    "NO_CONSENSUS",
    "ESCALATION_REQUIRED",
    "EXPORT_READY",
)
TERMINAL_PHASES = {"CONSENSUS_REACHED", "NO_CONSENSUS", "ESCALATION_REQUIRED", "EXPORT_READY"}
REASONING_STREAM_LIMIT = 8
PHASE_EVENT_LIMIT = 32


@dataclass(frozen=True)
class TribunalPhaseEvent:
    phase: str
    timestamp: str
    started_at: float
    previous_phase: str = ""
    previous_duration_seconds: float = 0.0

    def as_dict(self) -> Dict[str, object]:
        return {
            "phase": self.phase,
            "timestamp": self.timestamp,
            "started_at": round(self.started_at, 6),
            "previous_phase": self.previous_phase,
            "previous_duration_seconds": round(self.previous_duration_seconds, 6),
        }


THEME_REASONING_PHRASES: Dict[str, Dict[str, str]] = {
    "eva": {
        "CLASSIFYING": "MAGI classification lattice synchronized",
        "DISPATCHING": "CASPER/BALTHASAR/MELCHIOR dispatch nominal",
        "ANALYZING": "Pattern harmonization active",
        "DELIBERATING": "MAGI disagreement threshold monitored",
        "SYNTHESIZING": "Central Dogma verdict vector stabilizing",
        "CONSENSUS_REACHED": "MAGI synchronization nominal",
        "NO_CONSENSUS": "MAGI disagreement threshold exceeded",
        "ESCALATION_REQUIRED": "Human instrumentality review required",
        "EXPORT_READY": "Tribunal record sealed",
    },
    "nerv": {
        "CLASSIFYING": "MAGI classification lattice synchronized",
        "DISPATCHING": "CASPER/BALTHASAR/MELCHIOR dispatch nominal",
        "ANALYZING": "Pattern harmonization active",
        "DELIBERATING": "MAGI disagreement threshold monitored",
        "SYNTHESIZING": "Central Dogma verdict vector stabilizing",
        "CONSENSUS_REACHED": "MAGI synchronization nominal",
        "NO_CONSENSUS": "MAGI disagreement threshold exceeded",
        "ESCALATION_REQUIRED": "NERV tribunal escalation required",
        "EXPORT_READY": "NERV record sealed",
    },
    "wh40k": {
        "CLASSIFYING": "Cogitator taxonomy rite initiated",
        "DISPATCHING": "Noospheric dispatch sanctified",
        "ANALYZING": "Machine spirit divergence monitored",
        "DELIBERATING": "Logis conclave deliberation active",
        "SYNTHESIZING": "Arbiter canticle synthesizing",
        "CONSENSUS_REACHED": "Cogitator sanctification complete",
        "NO_CONSENSUS": "Machine spirit divergence detected",
        "ESCALATION_REQUIRED": "Holy synod review required",
        "EXPORT_READY": "Archive seal inscribed",
    },
    "military": {
        "CLASSIFYING": "Strategic classification underway",
        "DISPATCHING": "Chain of command dispatch complete",
        "ANALYZING": "Strategic branch validated",
        "DELIBERATING": "Escalation matrix synchronized",
        "SYNTHESIZING": "Command verdict vector locking",
        "CONSENSUS_REACHED": "Operational consensus achieved",
        "NO_CONSENSUS": "Command disagreement unresolved",
        "ESCALATION_REQUIRED": "Escalation authority required",
        "EXPORT_READY": "Briefing package ready",
    },
    "arasaka": {
        "CLASSIFYING": "Executive risk classification active",
        "DISPATCHING": "Corporate oversight channels dispatched",
        "ANALYZING": "Compliance lattice synchronized",
        "DELIBERATING": "Executive asset alignment rising",
        "SYNTHESIZING": "Board verdict synthesis active",
        "CONSENSUS_REACHED": "Executive risk alignment nominal",
        "NO_CONSENSUS": "Board consensus variance elevated",
        "ESCALATION_REQUIRED": "Executive escalation required",
        "EXPORT_READY": "Corporate dossier sealed",
    },
    "helldivers": {
        "CLASSIFYING": "Democratic authorization classified",
        "DISPATCHING": "Liberty command dispatch complete",
        "ANALYZING": "Patriotic analysis underway",
        "DELIBERATING": "Democratic authorization rising",
        "SYNTHESIZING": "Freedom verdict synthesis active",
        "CONSENSUS_REACHED": "Patriotism threshold stabilized",
        "NO_CONSENSUS": "Democracy variance unresolved",
        "ESCALATION_REQUIRED": "Super Earth command review required",
        "EXPORT_READY": "Liberty record approved",
    },
    "janus": {
        "CLASSIFYING": "Dual-vector classification active",
        "DISPATCHING": "Mirrored consensus dispatch complete",
        "ANALYZING": "Mirror branch conflict monitored",
        "DELIBERATING": "Dual-front deliberation active",
        "SYNTHESIZING": "Twin-core synthesis stabilizing",
        "CONSENSUS_REACHED": "Dual-vector convergence nominal",
        "NO_CONSENSUS": "Mirror branch conflict detected",
        "ESCALATION_REQUIRED": "Tribunal gatekeeper escalation required",
        "EXPORT_READY": "Janus dossier sealed",
    },
}

MONOLITH_PHASE_ACTIVITY = {
    "RATIONALIS": ("PARSING", "VALIDATING", "LOGIC MATRIX STABLE", "CONTRADICTION SCAN"),
    "AETERNUM": ("FORECASTING", "TEMPORAL BRANCH EXPANSION", "PROBABILISTIC HARMONICS", "VECTOR STABLE"),
    "BELLATOR": ("THREAT ASSESSMENT", "ESCALATION MATRIX", "TACTICAL CONVERGENCE", "RESPONSE GRID READY"),
    "ARBITER": ("CONSENSUS SYNCHRONIZATION", "VECTOR SYNTHESIS", "CONFIDENCE HARMONIZATION", "VERDICT LOCK"),
}


def validate_phase(phase: str) -> str:
    normalized = phase.upper()
    if normalized not in TRIBUNAL_PHASES:
        raise ValueError(f"Unknown tribunal phase: {phase}")
    return normalized


def build_phase_event(phase: str, previous_phase: str = "", previous_started_at: float = 0.0) -> TribunalPhaseEvent:
    now = time.perf_counter()
    duration = max(0.0, now - previous_started_at) if previous_phase and previous_started_at else 0.0
    return TribunalPhaseEvent(
        phase=validate_phase(phase),
        timestamp=datetime.now().isoformat(timespec="seconds"),
        started_at=now,
        previous_phase=previous_phase,
        previous_duration_seconds=duration,
    )


def append_bounded_event(events: List[Dict[str, object]], event: TribunalPhaseEvent, limit: int = PHASE_EVENT_LIMIT) -> None:
    events.append(event.as_dict())
    if len(events) > limit:
        del events[: len(events) - limit]


def theme_reasoning_phrase(theme_key: str, phase: str) -> str:
    normalized_theme = theme_key.lower()
    normalized_phase = validate_phase(phase)
    return THEME_REASONING_PHRASES.get(normalized_theme, THEME_REASONING_PHRASES["military"]).get(
        normalized_phase,
        f"Tribunal phase {normalized_phase.lower()}",
    )


def append_reasoning_event(events: List[str], message: str, limit: int = REASONING_STREAM_LIMIT) -> None:
    clean = " ".join(str(message).split())
    if not clean:
        return
    if events and events[-1] == clean:
        return
    events.append(clean)
    if len(events) > limit:
        del events[: len(events) - limit]


def phase_for_verdict(verdict: FinalVerdict, terminal_branch: str = "", review_triggers: Iterable[str] | None = None) -> str:
    normalized_verdict = verdict.value.upper()
    normalized_branch = terminal_branch.upper()
    triggers = " ".join(str(trigger).upper() for trigger in (review_triggers or ()))
    if normalized_verdict == "NO_CONSENSUS" or "NO_CONSENSUS" in normalized_branch:
        return "NO_CONSENSUS"
    if normalized_verdict in {"ESCALATE", "ERROR", "HUMAN_REVIEW_REQUIRED"}:
        return "ESCALATION_REQUIRED"
    if "ESCALAT" in normalized_branch or "ESCALAT" in triggers:
        return "ESCALATION_REQUIRED"
    return "CONSENSUS_REACHED"


def convergence_percent(votes: Dict[str, Vote]) -> float:
    if not votes:
        return 0.0
    counts: Dict[str, int] = {}
    confidence_total = 0.0
    for vote in votes.values():
        counts[vote.vote.value] = counts.get(vote.vote.value, 0) + 1
        confidence_total += max(0.0, min(1.0, float(vote.confidence)))
    agreement = max(counts.values()) / len(votes)
    confidence = confidence_total / len(votes)
    return round(max(0.0, min(1.0, (agreement * 0.55) + (confidence * 0.45))), 4)


def monolith_activity_phrase(agent_id: str, index: int = 0) -> str:
    phrases = MONOLITH_PHASE_ACTIVITY.get(agent_id.upper(), ("ANALYZING",))
    return phrases[index % len(phrases)]
