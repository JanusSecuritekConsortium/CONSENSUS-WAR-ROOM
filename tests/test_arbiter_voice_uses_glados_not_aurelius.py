from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models import FinalVerdict, TribunalResult
from voice.arbiter_verdict_voice import ARBITER_VOICE_PROFILE, build_arbiter_voice_dispatch


def test_arbiter_dispatch_uses_glados_profile_not_aurelius() -> None:
    result = TribunalResult(
        query="dummy",
        verdict=FinalVerdict.APPROVE,
        confidence=0.9,
        reason="Approved.",
        votes={},
        vote_distribution={},
        quorum_met=True,
        review_triggers=[],
        session_id="voice-glados",
        theme="military",
    )
    dispatch = build_arbiter_voice_dispatch(result)
    assert dispatch.backend == ARBITER_VOICE_PROFILE
    assert dispatch.backend == "ARBITER_GLADOS"
    assert "AURELIUS" not in dispatch.backend
    assert dispatch.text == "Consensus reached. Proposal approved."


if __name__ == "__main__":
    test_arbiter_dispatch_uses_glados_profile_not_aurelius()
    print("test_arbiter_voice_uses_glados_not_aurelius PASS")
