from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models import FinalVerdict, TribunalResult
from voice.arbiter_verdict_voice import build_arbiter_voice_dispatch


def test_no_consensus_announcement_text_is_terminal_deadlock() -> None:
    result = TribunalResult(
        query="dummy",
        verdict=FinalVerdict.NO_CONSENSUS,
        confidence=0.0,
        reason="No consensus.",
        votes={},
        vote_distribution={},
        quorum_met=False,
        review_triggers=[],
        session_id="voice-no-consensus",
        theme="military",
        terminal_branch="no_consensus",
    )
    dispatch = build_arbiter_voice_dispatch(result)
    assert dispatch.terminal_state == "NO_CONSENSUS"
    assert dispatch.text == "Tribunal deadlock. No consensus reached. Manual review recommended."


if __name__ == "__main__":
    test_no_consensus_announcement_text_is_terminal_deadlock()
    print("test_arbiter_voice_announces_no_consensus PASS")
