from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models import FinalVerdict, TribunalResult
from voice.arbiter_verdict_voice import build_arbiter_voice_dispatch


def test_classification_failure_has_explicit_operator_review_text() -> None:
    result = TribunalResult(
        query="dummy",
        verdict=FinalVerdict.NO_CONSENSUS,
        confidence=0.0,
        reason="Classification failed.",
        votes={},
        vote_distribution={},
        quorum_met=False,
        review_triggers=["classification_failure"],
        session_id="voice-classification-failure",
        theme="military",
        terminal_branch="classification_failure",
        proposal_classification={"status": "FAILED", "reason": "confidence below threshold"},
    )
    dispatch = build_arbiter_voice_dispatch(result)
    assert dispatch.terminal_state == "CLASSIFICATION_FAILURE"
    assert dispatch.text == "Classification failure. Proposal taxonomy could not be resolved. Escalating to operator review."


if __name__ == "__main__":
    test_classification_failure_has_explicit_operator_review_text()
    print("test_arbiter_voice_announces_classification_failure PASS")
