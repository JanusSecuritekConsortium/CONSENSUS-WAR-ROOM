from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Dict, List

from core.models import FinalVerdict, TribunalResult, Vote, VoteValue
from core.voting.classifier import assign_critical_domain_relevance, classify_proposal
from core.voting.rules import (
    ConsensusRules,
    average_confidence,
    consensus_confidence,
    majority_result,
    priority_ordered_votes,
    summarize_reason,
)


class ConsensusEngine:
    def __init__(self, rules: ConsensusRules, theme_key: str) -> None:
        self.rules = rules
        self.theme_key = theme_key

    def calculate_result(self, query: str, votes: Dict[str, Vote], session_id: str) -> TribunalResult:
        review_triggers: List[str] = []
        voting_votes = list(votes.values())
        distribution = Counter(v.vote.value for v in voting_votes)
        classification_result = classify_proposal(
            query,
            taxonomy=self.rules.proposal_taxonomy,
            confidence_threshold=self.rules.classification_confidence_threshold,
        )

        if not classification_result.ok:
            branch = "classification_failure_critical_risk" if any(v.critical_risk for v in voting_votes) else "classification_failure"
            review_triggers.append(branch)
            return TribunalResult(
                query=query,
                verdict=FinalVerdict.ESCALATE if branch == "classification_failure_critical_risk" else FinalVerdict.NO_CONSENSUS,
                confidence=average_confidence(voting_votes),
                reason=f"Proposal classification failed: {classification_result.failure_reason}.",
                votes=votes,
                vote_distribution=dict(distribution),
                quorum_met=True,
                review_triggers=review_triggers,
                session_id=session_id,
                theme=self.theme_key,
                terminal_branch=branch,
                proposal_classification={"status": "FAILED", "reason": classification_result.failure_reason},
            )

        classification = classification_result.classification
        classification_payload = classification.to_dict() if classification else {}
        assign_critical_domain_relevance(
            voting_votes,
            classification.proposal_classes if classification else (),
            self.rules.monolith_domain_map,
        )

        decided = majority_result(voting_votes)
        if decided is not None:
            verdict = FinalVerdict.APPROVE if decided == VoteValue.APPROVE else FinalVerdict.DENY
            matching_count = sum(1 for vote in voting_votes if vote.vote == decided)
            return TribunalResult(
                query=query,
                verdict=verdict,
                confidence=consensus_confidence(decided, voting_votes),
                reason=summarize_reason(decided, matching_count, votes, review_triggers),
                votes=votes,
                vote_distribution=dict(distribution),
                quorum_met=True,
                review_triggers=review_triggers,
                session_id=session_id,
                theme=self.theme_key,
                terminal_branch="majority",
                proposal_classification=classification_payload,
            )

        if any(vote.critical_risk for vote in voting_votes):
            review_triggers.append("unresolved_critical_risk")
            return self._terminal_result(
                query,
                FinalVerdict.CAUTION,
                "UNRESOLVED tribunal with critical risk reported.",
                votes,
                distribution,
                review_triggers,
                session_id,
                "tie_break_caution",
                classification_payload,
            )

        mean_evidence = mean(vote.evidence_quality for vote in voting_votes) if voting_votes else 0.0
        domain_critical_starved = any(
            vote.critical_domain_relevance and vote.evidence_quality < self.rules.evidence_threshold
            for vote in voting_votes
        )
        if mean_evidence < self.rules.evidence_threshold or domain_critical_starved:
            review_triggers.append("insufficient_evidence")
            if domain_critical_starved:
                review_triggers.append("domain_critical_evidence_starved")
            return self._terminal_result(
                query,
                FinalVerdict.NO_CONSENSUS,
                "UNRESOLVED tribunal with insufficient evidence quality.",
                votes,
                distribution,
                review_triggers,
                session_id,
                "tie_break_no_consensus",
                classification_payload,
            )

        for vote in priority_ordered_votes(voting_votes, self.rules.tie_break_priority):
            if vote.vote in {VoteValue.APPROVE, VoteValue.DENY}:
                verdict = FinalVerdict.APPROVE if vote.vote == VoteValue.APPROVE else FinalVerdict.DENY
                review_triggers.append(f"priority_tie_break:{vote.node_key}")
                return self._terminal_result(
                    query,
                    verdict,
                    f"UNRESOLVED tribunal resolved by priority monolith {vote.node_key}.",
                    votes,
                    distribution,
                    review_triggers,
                    session_id,
                    "tie_break_priority",
                    classification_payload,
                )

        review_triggers.append("all_abstain")
        return self._terminal_result(
            query,
            FinalVerdict.NO_CONSENSUS,
            "All voting monoliths abstained.",
            votes,
            distribution,
            review_triggers,
            session_id,
            "tie_break_all_abstain",
            classification_payload,
        )

    def _terminal_result(
        self,
        query: str,
        verdict: FinalVerdict,
        reason: str,
        votes: Dict[str, Vote],
        distribution: Counter,
        review_triggers: List[str],
        session_id: str,
        branch: str,
        classification_payload: Dict[str, object],
    ) -> TribunalResult:
        return TribunalResult(
            query=query,
            verdict=verdict,
            confidence=average_confidence(votes.values()),
            reason=reason,
            votes=votes,
            vote_distribution=dict(distribution),
            quorum_met=True,
            review_triggers=review_triggers,
            session_id=session_id,
            theme=self.theme_key,
            terminal_branch=branch,
            proposal_classification=classification_payload,
        )
