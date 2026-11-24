from __future__ import annotations

from config.names import AETERNUM, BELLATOR, RATIONALIS
from core.models import FinalVerdict, Vote, VoteValue
from core.voting.engine import ConsensusEngine
from core.voting.rules import ConsensusRules

QUERY = "Should the library open on Sundays?"


def _vote(key, value, confidence, evidence=0.8, errors=None):
    return Vote(node_key=key, role=key, vote=value, confidence=confidence, reasoning="r",
                evidence_quality=evidence, validation_errors=list(errors or []))


def _check(votes):
    engine = ConsensusEngine(ConsensusRules(), "eva")
    return engine.rerun_check(QUERY)(votes), engine.calculate_result(QUERY, votes, "t").verdict


def test_a_majority_that_arbiter_would_reject_reruns():
    # Codex review 2026-11-24: two 0.70 approvals against a 0.90 denial is a majority, but ARBITER returns NO_CONSENSUS.
    votes = {RATIONALIS: _vote(RATIONALIS, VoteValue.APPROVE, 0.70), AETERNUM: _vote(AETERNUM, VoteValue.APPROVE, 0.70),
             BELLATOR: _vote(BELLATOR, VoteValue.DENY, 0.90)}
    settled, verdict = _check(votes)
    assert verdict == FinalVerdict.NO_CONSENSUS and settled is False


def test_a_majority_with_weak_evidence_reruns():
    votes = {key: _vote(key, VoteValue.APPROVE, 0.85, evidence=0.1) for key in (RATIONALIS, AETERNUM, BELLATOR)}
    settled, verdict = _check(votes)
    assert verdict == FinalVerdict.NO_CONSENSUS and settled is False


def test_an_accepted_majority_stops():
    votes = {key: _vote(key, VoteValue.APPROVE, 0.85) for key in (RATIONALIS, AETERNUM, BELLATOR)}
    settled, verdict = _check(votes)
    assert verdict == FinalVerdict.APPROVE and settled is True


def test_no_majority_reruns_and_a_failed_round_stops():
    split = {RATIONALIS: _vote(RATIONALIS, VoteValue.APPROVE, 0.9), AETERNUM: _vote(AETERNUM, VoteValue.DENY, 0.9),
             BELLATOR: _vote(BELLATOR, VoteValue.ABSTAIN, 0.4)}
    assert _check(split)[0] is False
    failed = {**split, BELLATOR: _vote(BELLATOR, VoteValue.ABSTAIN, 0.0, errors=["missing VOTE"])}
    assert _check(failed)[0] is True

