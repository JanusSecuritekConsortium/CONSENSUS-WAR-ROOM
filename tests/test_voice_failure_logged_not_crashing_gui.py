from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models import FinalVerdict, TribunalResult
from voice import arbiter_verdict_voice


class FailingGlados:
    def speak(self, _text: str):
        raise RuntimeError("voice offline")


def test_voice_failure_returns_failed_dispatch_without_crash() -> None:
    arbiter_verdict_voice.reset_arbiter_voice_dispatch_cache()
    original_log = arbiter_verdict_voice._log_dispatch
    arbiter_verdict_voice._log_dispatch = lambda *args, **kwargs: None
    try:
        result = TribunalResult(
            query="dummy",
            verdict=FinalVerdict.ERROR,
            confidence=0.0,
            reason="Error.",
            votes={},
            vote_distribution={},
            quorum_met=False,
            review_triggers=[],
            session_id="voice-failure",
            theme="military",
        )

        dispatch = arbiter_verdict_voice.dispatch_arbiter_verdict_voice(result, async_dispatch=False, adapter_factory=FailingGlados)

        assert dispatch.status == "failed"
        assert dispatch.degraded_reason == "voice offline"
        assert dispatch.text == "Tribunal error. Decision pipeline failed."
    finally:
        arbiter_verdict_voice._log_dispatch = original_log


if __name__ == "__main__":
    test_voice_failure_returns_failed_dispatch_without_crash()
    print("test_voice_failure_logged_not_crashing_gui PASS")
