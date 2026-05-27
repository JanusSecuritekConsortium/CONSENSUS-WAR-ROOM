from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class SpeechEventType(str, Enum):
    APPOINTMENT_CREATED = "appointment_created"
    APPOINTMENT_REMINDER = "appointment_reminder"
    APPOINTMENT_SUMMARY = "appointment_summary"
    CONSENSUS_APPROVED = "consensus_approved"
    CONSENSUS_DENIED = "consensus_denied"
    CONSENSUS_CONDITIONAL_APPROVAL = "consensus_conditional_approval"
    CONSENSUS_HUMAN_REVIEW_REQUIRED = "consensus_human_review_required"
    CONSENSUS_ABSTAINED = "consensus_abstained"
    CONSENSUS_NO_CONSENSUS = "consensus_no_consensus"
    CONSENSUS_CAUTION = "consensus_caution"
    CONSENSUS_ESCALATE = "consensus_escalate"
    CONSENSUS_DEADLOCK = "consensus_deadlock"
    SYSTEM_NOTICE = "system_notice"


@dataclass
class SpeechEvent:
    event_type: SpeechEventType
    text: str
    priority: int = 5
    source: str = "AURELIUS"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


def consensus_event_type(verdict: object) -> SpeechEventType:
    value = getattr(verdict, "value", verdict)
    normalized = str(value).upper()
    mapping = {
        "APPROVE": SpeechEventType.CONSENSUS_APPROVED,
        "APPROVED": SpeechEventType.CONSENSUS_APPROVED,
        "DENY": SpeechEventType.CONSENSUS_DENIED,
        "DENIED": SpeechEventType.CONSENSUS_DENIED,
        "CONDITIONAL": SpeechEventType.CONSENSUS_CONDITIONAL_APPROVAL,
        "CONDITIONAL_APPROVAL": SpeechEventType.CONSENSUS_CONDITIONAL_APPROVAL,
        "ABSTAIN": SpeechEventType.CONSENSUS_ABSTAINED,
        "NO_CONSENSUS": SpeechEventType.CONSENSUS_NO_CONSENSUS,
        "CAUTION": SpeechEventType.CONSENSUS_CAUTION,
        "ESCALATE": SpeechEventType.CONSENSUS_ESCALATE,
        "HUMAN_REVIEW_REQUIRED": SpeechEventType.CONSENSUS_HUMAN_REVIEW_REQUIRED,
        "DEADLOCK": SpeechEventType.CONSENSUS_DEADLOCK,
        "ERROR": SpeechEventType.CONSENSUS_DEADLOCK,
    }
    return mapping.get(normalized, SpeechEventType.CONSENSUS_DEADLOCK)
