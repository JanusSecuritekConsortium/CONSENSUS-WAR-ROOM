from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models import FinalVerdict, TribunalResult
from voice import arbiter_verdict_voice


class GeneratedOnlyGlados:
    def speak(self, _text: str):
        class Result:
            ok = True
            mode = "rvc"
            audio_path = "arbiter_generated.wav"
            metadata = {"playback": "skipped", "played": False}

        return Result()


def test_generated_audio_without_playback_is_not_logged_as_success() -> None:
    arbiter_verdict_voice.reset_arbiter_voice_dispatch_cache()
    original_log = arbiter_verdict_voice._log_dispatch
    arbiter_verdict_voice._log_dispatch = lambda *args, **kwargs: None
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
            session_id="voice-generated-only",
            theme="military",
        )

        dispatch = arbiter_verdict_voice.dispatch_arbiter_verdict_voice(
            result,
            async_dispatch=False,
            adapter_factory=GeneratedOnlyGlados,
        )

        assert dispatch.status == "degraded"
        assert dispatch.degraded_reason == "audio generated but playback was not confirmed"
    finally:
        arbiter_verdict_voice._log_dispatch = original_log


if __name__ == "__main__":
    test_generated_audio_without_playback_is_not_logged_as_success()
    print("test_arbiter_voice_playback_confirmation PASS")
