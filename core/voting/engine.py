from __future__ import annotations

from collections import Counter
from typing import Dict, List

from core.models import FinalVerdict, TribunalResult, Vote, VoteValue
from core.voting.rules import (
    ConsensusRules,
    average_confidence,
    consensus_confidence,
    should_force_review,
    summarize_reason,
)


class ConsensusEngine:
    def __init__(self, rules: ConsensusRules, theme_key: str) -> None:
        self.rules = rules
        self.theme_key = theme_key

    def calculate_result(self, query: str, votes: Dict[str, Vote], session_id: str) -> TribunalResult:
        review_triggers: List[str] = []
        qualified = {
            key: vote
            for key, vote in votes.items()
            if vote.vote != VoteValue.ERROR and vote.confidence >= self.rules.minimum_confidence
        }

        quorum_met = len(qualified) >= self.rules.quorum
        distribution = Counter(v.vote.value for v in votes.values())
        qualified_distribution = Counter(v.vote for v in qualified.values())

        if not quorum_met:
            review_triggers.append("quorum_not_met")
            return TribunalResult(
                query=query,
                verdict=FinalVerdict.HUMAN_REVIEW_REQUIRED,
                confidence=average_confidence(votes.values()),
                reason=f"Only {len(qualified)} qualified votes met confidence threshold.",
                votes=votes,
                vote_distribution=dict(distribution),
                quorum_met=False,
                review_triggers=review_triggers,
                session_id=session_id,
                theme=self.theme_key,
            )

        if distribution[VoteValue.ERROR.value] > 0:
            review_triggers.append("node_error")

        top_vote, top_count = qualified_distribution.most_common(1)[0]
        if top_count < self.rules.majority:
            review_triggers.append("no_majority")
            return TribunalResult(
                query=query,
                verdict=FinalVerdict.DEADLOCK,
                confidence=average_confidence(qualified.values()),
                reason="Qualified votes did not produce a two-of-three majority.",
                votes=votes,
                vote_distribution=dict(distribution),
                quorum_met=True,
                review_triggers=review_triggers,
                session_id=session_id,
                theme=self.theme_key,
            )

        if top_vote == VoteValue.APPROVE:
            verdict = FinalVerdict.APPROVED
        elif top_vote == VoteValue.DENY:
            verdict = FinalVerdict.DENIED
        elif top_vote == VoteValue.CONDITIONAL:
            verdict = FinalVerdict.CONDITIONAL_APPROVAL
            review_triggers.append("conditions_attached")
        elif top_vote == VoteValue.ESCALATE:
            verdict = FinalVerdict.HUMAN_REVIEW_REQUIRED
            review_triggers.append("monolith_escalation")
        else:
            verdict = FinalVerdict.HUMAN_REVIEW_REQUIRED
            review_triggers.append("majority_abstained")

        if self.rules.high_risk_review and should_force_review(votes):
            verdict = FinalVerdict.HUMAN_REVIEW_REQUIRED
            review_triggers.append("security_finance_or_escalation_review")

        confidence = consensus_confidence(top_vote, qualified.values())
        reason = summarize_reason(top_vote, top_count, qualified, review_triggers)

        return TribunalResult(
            query=query,
            verdict=verdict,
            confidence=confidence,
            reason=reason,
            votes=votes,
            vote_distribution=dict(distribution),
            quorum_met=True,
            review_triggers=review_triggers,
            session_id=session_id,
            theme=self.theme_key,
        )

