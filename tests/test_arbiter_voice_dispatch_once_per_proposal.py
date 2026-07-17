from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models import FinalVerdict, TribunalResult
from voice import arbiter_verdict_voice


class DummyGlados:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def speak(self, text: str):
        self.calls.append(text)

        class Result:
            ok = True
            mode = "rvc"
            audio_path = "arbiter.wav"
            metadata = {"playback": "winsound", "played": True}

        return Result()


def test_dispatch_is_once_per_proposal_id() -> None:
    arbiter_verdict_voice.reset_arbiter_voice_dispatch_cache()
    original_log = arbiter_verdict_voice._log_dispatch
    arbiter_verdict_voice._log_dispatch = lambda *args, **kwargs: None
    calls: list[str] = []
    try:
        result = TribunalResult(
            query="dummy",
            verdict=FinalVerdict.NO_CONSENSUS,
            confidence=0.0,
            reason="No consensus.",
            votes={},
            vote_distribution={},
            quorum_met=False,
            review_triggers=[],
            session_id="voice-once",
            theme="military",
        )

        first = arbiter_verdict_voice.dispatch_arbiter_verdict_voice(result, async_dispatch=False, adapter_factory=lambda: DummyGlados(calls))
        second = arbiter_verdict_voice.dispatch_arbiter_verdict_voice(result, async_dispatch=False, adapter_factory=lambda: DummyGlados(calls))

        assert first.status == "success"
        assert second.status == "duplicate_suppressed"
        assert len(calls) == 1
    finally:
        arbiter_verdict_voice._log_dispatch = original_log


if __name__ == "__main__":
    test_dispatch_is_once_per_proposal_id()
    print("test_arbiter_voice_dispatch_once_per_proposal PASS")
