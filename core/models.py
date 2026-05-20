from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


class VoteValue(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"
    NO_CONSENSUS = "NO_CONSENSUS"
    CAUTION = "CAUTION"
    ESCALATE = "ESCALATE"
    # Legacy/runtime-only values kept for history migration and defensive UI handling.
    CONDITIONAL = "CONDITIONAL"
    ERROR = "ERROR"


class FinalVerdict(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"
    NO_CONSENSUS = "NO_CONSENSUS"
    CAUTION = "CAUTION"
    ESCALATE = "ESCALATE"
    # Legacy verdicts kept so older history and integrations can still deserialize.
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    CONDITIONAL_APPROVAL = "CONDITIONAL_APPROVAL"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DEADLOCK = "DEADLOCK"
    ERROR = "ERROR"


@dataclass(frozen=True)
class NodeIdentity:
    role: str
    codename: str
    core_name: str
    monolith_name: str
    symbol: str
    model: str
    temperature: float
    mission: str
    prompt: str


@dataclass(frozen=True)
class Theme:
    key: str
    display_name: str
    aliases: List[str]
    primary_color: str
    secondary_color: str
    accent_color: str
    background_color: str
    surface_color: str
    text_color: str
    warning_color: str
    error_color: str
    font_family: str
    logo_id: str
    logo_path: str
    boot_profile_id: str
    loading_animation_type: str
    panel_style: str
    border_style: str
    monolith_labels: Dict[str, Dict[str, str]]
    interface_labels: Dict[str, str]
    muted_text: str = ""
    secondary_text: str = ""
    panel_label: str = ""
    panel_value: str = ""

    @property
    def title(self) -> str:
        return self.display_name

    @property
    def palette(self) -> Dict[str, str]:
        return {
            "primary": self.primary_color,
            "secondary": self.secondary_color,
            "accent": self.accent_color,
            "background": self.background_color,
            "surface": self.surface_color,
            "text": self.text_color,
            "warning": self.warning_color,
            "error": self.error_color,
            "muted_text": self.muted_text,
            "secondary_text": self.secondary_text,
            "panel_label": self.panel_label,
            "panel_value": self.panel_value,
        }

    @property
    def logo(self) -> str:
        return Path(self.logo_path).read_text(encoding="utf-8")

    @property
    def boot_lines(self) -> List[str]:
        from ui.themes.boot_profiles import get_boot_profile

        return list(get_boot_profile(self.boot_profile_id).boot_lines)


@dataclass
class Vote:
    node_key: str
    role: str
    vote: VoteValue
    confidence: float
    reasoning: str
    evidence_quality: float = 0.0
    critical_risk: bool = False
    critical_domain_relevance: Optional[bool] = None
    validation_errors: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    model: str = "mock"
    response_time: float = 0.0
    raw_response: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TribunalResult:
    query: str
    verdict: FinalVerdict
    confidence: float
    reason: str
    votes: Dict[str, Vote]
    vote_distribution: Dict[str, int]
    quorum_met: bool
    review_triggers: List[str]
    session_id: str
    theme: str
    terminal_branch: str = ""
    proposal_classification: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class LLMBackend(Protocol):
    name: str

    def complete(self, node: NodeIdentity, query: str, context: Dict[str, Any]) -> str:
        """Return raw model text for one node."""
