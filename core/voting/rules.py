from __future__ import annotations

from typing import Dict, Iterable, List

from config.names import AETERNUM, BELLATOR
from core.models import Vote, VoteValue


class ConsensusRules:
    def __init__(
        self,
        minimum_confidence: float = 0.6,
        quorum: int = 2,
        majority: int = 2,
        high_risk_review: bool = True,
    ):
        self.minimum_confidence = minimum_confidence
        self.quorum = quorum
        self.majority = majority
        self.high_risk_review = high_risk_review


def average_confidence(votes: Iterable[Vote]) -> float:
    values = [vote.confidence for vote in votes]
    return round(sum(values) / len(values), 4) if values else 0.0


def consensus_confidence(winning_vote: VoteValue, qualified_votes: Iterable[Vote]) -> float:
    votes = list(qualified_votes)
    matching = [vote.confidence for vote in votes if vote.vote == winning_vote]
    opposing = [vote.confidence for vote in votes if vote.vote != winning_vote]
    if not matching:
        return 0.0
    base = sum(matching) / len(matching)
    opposition_penalty = (sum(opposing) / max(1, len(opposing))) * 0.15 if opposing else 0.0
    unanimity_bonus = 0.08 if len(matching) == len(votes) else 0.0
    return round(max(0.0, min(0.99, base - opposition_penalty + unanimity_bonus)), 4)


def should_force_review(votes: Dict[str, Vote]) -> bool:
    security = votes.get(BELLATOR)
    finance = votes.get(AETERNUM)
    if security and security.vote == VoteValue.DENY and security.confidence >= 0.75:
        return True
    if finance and finance.vote == VoteValue.DENY and finance.confidence >= 0.85:
        return True
    if any(vote.vote == VoteValue.ESCALATE for vote in votes.values()):
        return True
    return False


def summarize_reason(
    top_vote: VoteValue,
    top_count: int,
    qualified: Dict[str, Vote],
    review_triggers: List[str],
) -> str:
    parts = [f"{top_vote.value} received {top_count} qualified votes."]
    if review_triggers:
        parts.append("Review triggers: " + ", ".join(review_triggers) + ".")
    for key, vote in qualified.items():
        parts.append(f"{key}: {vote.vote.value} at {vote.confidence:.0%}.")
    return " ".join(parts)
