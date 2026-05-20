from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import AETERNUM, BELLATOR, RATIONALIS
from core.models import FinalVerdict, Vote, VoteValue
from core.voting.engine import ConsensusEngine
from core.voting.parser import parse_vote
from core.voting.rules import ConsensusRules
from config.nodes import DEFAULT_NODES


RULES = ConsensusRules(
    evidence_threshold=0.4,
    classification_confidence_threshold=0.6,
    tie_break_priority=[BELLATOR, RATIONALIS, AETERNUM],
)


def vote(agent_id: str, value: VoteValue, evidence: float = 0.9, risk: bool = False) -> Vote:
    node = DEFAULT_NODES[agent_id]
    return Vote(
        node_key=agent_id,
        role=node.role,
        vote=value,
        confidence=0.8,
        reasoning="test vote",
        evidence_quality=evidence,
        critical_risk=risk,
        model="test",
    )


def resolve(votes: dict[str, Vote], query: str = "security breach threat exploit vulnerability intrusion"):
    return ConsensusEngine(RULES, "military").calculate_result(query, votes, "spec-test")


def test_parser_rejects_arbiter_only_monolith_result() -> None:
    parsed = parse_vote(
        "VOTE: ESCALATE\nCONFIDENCE: 0.9\nEVIDENCE_QUALITY: 0.9\nCRITICAL_RISK: false\nRATIONALE: bad schema",
        DEFAULT_NODES[BELLATOR],
        0.0,
        "mock",
    )

    assert parsed.vote == VoteValue.ABSTAIN
    assert parsed.evidence_quality == 0.0
    assert parsed.critical_risk is False
    assert parsed.validation_errors


def test_majority_short_circuits_tie_break_even_with_low_evidence() -> None:
    result = resolve(
        {
            RATIONALIS: vote(RATIONALIS, VoteValue.APPROVE, evidence=0.1),
            AETERNUM: vote(AETERNUM, VoteValue.APPROVE, evidence=0.1),
            BELLATOR: vote(BELLATOR, VoteValue.DENY, evidence=0.1, risk=True),
        }
    )

    assert result.verdict == FinalVerdict.APPROVE
    assert result.terminal_branch == "majority"


def test_unresolved_critical_risk_returns_caution() -> None:
    result = resolve(
        {
            RATIONALIS: vote(RATIONALIS, VoteValue.APPROVE),
            AETERNUM: vote(AETERNUM, VoteValue.DENY),
            BELLATOR: vote(BELLATOR, VoteValue.ABSTAIN, risk=True),
        }
    )

    assert result.verdict == FinalVerdict.CAUTION
    assert result.terminal_branch == "tie_break_caution"


def test_unresolved_domain_critical_low_evidence_returns_no_consensus() -> None:
    result = resolve(
        {
            RATIONALIS: vote(RATIONALIS, VoteValue.APPROVE, evidence=0.9),
            AETERNUM: vote(AETERNUM, VoteValue.DENY, evidence=0.9),
            BELLATOR: vote(BELLATOR, VoteValue.ABSTAIN, evidence=0.1),
        }
    )

    assert result.verdict == FinalVerdict.NO_CONSENSUS
    assert "domain_critical_evidence_starved" in result.review_triggers


def test_unresolved_high_evidence_uses_priority() -> None:
    result = resolve(
        {
            RATIONALIS: vote(RATIONALIS, VoteValue.APPROVE),
            AETERNUM: vote(AETERNUM, VoteValue.ABSTAIN),
            BELLATOR: vote(BELLATOR, VoteValue.DENY),
        }
    )

    assert result.verdict == FinalVerdict.DENY
    assert result.terminal_branch == "tie_break_priority"


def test_classification_failure_blocks_clean_majority() -> None:
    result = resolve(
        {
            RATIONALIS: vote(RATIONALIS, VoteValue.APPROVE),
            AETERNUM: vote(AETERNUM, VoteValue.APPROVE),
            BELLATOR: vote(BELLATOR, VoteValue.APPROVE),
        },
        query="xyzzy plugh frobnicate",
    )

    assert result.verdict == FinalVerdict.NO_CONSENSUS
    assert result.terminal_branch == "classification_failure"


if __name__ == "__main__":
    test_parser_rejects_arbiter_only_monolith_result()
    test_majority_short_circuits_tie_break_even_with_low_evidence()
    test_unresolved_critical_risk_returns_caution()
    test_unresolved_domain_critical_low_evidence_returns_no_consensus()
    test_unresolved_high_evidence_uses_priority()
    test_classification_failure_blocks_clean_majority()
    print("test_consensus_spec_engine PASS")
