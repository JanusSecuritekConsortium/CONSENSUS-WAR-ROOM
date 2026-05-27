from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from config.names import AETERNUM, BELLATOR, RATIONALIS
from core.models import Vote, VoteValue


class ConsensusRules:
    def __init__(
        self,
        minimum_confidence: float = 0.6,
        quorum: int = 2,
        majority: int = 2,
        high_risk_review: bool = True,
        evidence_threshold: float = 0.4,
        classification_confidence_threshold: float = 0.6,
        tie_break_priority: Sequence[str] | None = None,
        proposal_taxonomy: Sequence[str] | None = None,
        monolith_domain_map: Dict[str, List[str]] | None = None,
    ):
        self.minimum_confidence = minimum_confidence
        self.quorum = quorum
        self.majority = majority
        self.high_risk_review = high_risk_review
        self.evidence_threshold = evidence_threshold
        self.classification_confidence_threshold = classification_confidence_threshold
        self.tie_break_priority = list(tie_break_priority or [BELLATOR, RATIONALIS, AETERNUM])
        self.proposal_taxonomy = list(
            proposal_taxonomy
            or [
                "logic",
                "governance",
                "ethics",
                "analysis",
                "finance",
                "forecasting",
                "economics",
                "historical_patterns",
                "security",
                "geopolitics",
                "risk",
                "operations",
            ]
        )
        self.monolith_domain_map = dict(
            monolith_domain_map
            or {
                RATIONALIS: ["logic", "governance", "ethics", "analysis"],
                AETERNUM: ["finance", "forecasting", "economics", "historical_patterns"],
                BELLATOR: ["security", "geopolitics", "risk", "operations"],
            }
        )


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


def majority_threshold(voting_count: int) -> int:
    return (voting_count // 2) + 1


def majority_result(votes: Sequence[Vote]) -> Optional[VoteValue]:
    threshold = majority_threshold(len(votes))
    approve = sum(1 for vote in votes if vote.vote == VoteValue.APPROVE)
    deny = sum(1 for vote in votes if vote.vote == VoteValue.DENY)
    if approve >= threshold and deny < threshold:
        return VoteValue.APPROVE
    if deny >= threshold and approve < threshold:
        return VoteValue.DENY
    return None


def confidence_qualified_votes(votes: Sequence[Vote], minimum_confidence: float) -> List[Vote]:
    return [
        vote
        for vote in votes
        if not vote.validation_errors and vote.confidence >= minimum_confidence
    ]


def priority_ordered_votes(votes: Sequence[Vote], priority: Sequence[str]) -> List[Vote]:
    by_name = {vote.node_key: vote for vote in votes}
    ordered: List[Vote] = []
    seen: set[str] = set()
    for name in priority:
        vote = by_name.get(name)
        if vote is not None and name not in seen:
            ordered.append(vote)
            seen.add(name)
    for vote in votes:
        if vote.node_key not in seen:
            ordered.append(vote)
            seen.add(vote.node_key)
    return ordered


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
