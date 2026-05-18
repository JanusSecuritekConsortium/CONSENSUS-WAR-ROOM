from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assistant.aurelius_runtime import AureliusRuntime
from config.version import SYSTEM_VERSION


class DummyTTS:
    def synthesize(self, text: str):
        class Result:
            ok = True
            audio_path = "dummy.wav"

        return Result()


def test_aurelius_direct_reply_and_tts() -> None:
    runtime = AureliusRuntime(tts_adapter=DummyTTS(), voice_adapter=None)
    runtime.set_voice_loop(True)
    result = runtime.handle_text("hello", speak=True, route_to_consensus=False)
    assert "A.U.R.E.L.I.U.S." in result.text
    assert result.spoken is True
    assert result.audio_path == "dummy.wav"
    assert result.routed_to_consensus is False


def test_aurelius_status_uses_system_version() -> None:
    runtime = AureliusRuntime(tts_adapter=None, voice_adapter=None)
    status = runtime.status()
    assert status["version"] == SYSTEM_VERSION
    assert status["runtime"] == "AURELIUS"
    assert status["voice_loop_enabled"] is False


def test_aurelius_does_not_resolve_provider_or_models() -> None:
    source = inspect.getsource(AureliusRuntime)
    forbidden = (
        "health_check(",
        "list_models(",
        "check_models(",
        "provider_status",
        "MSTY_BASE_URL",
        "OLLAMA_BASE_URL",
    )
    for token in forbidden:
        assert token not in source


def test_aurelius_voice_soft_fails_without_adapter() -> None:
    runtime = AureliusRuntime(tts_adapter=None, voice_adapter=None)
    result = runtime.poll_voice_once()
    assert result.metadata["error"] == "voice_adapter_missing"


if __name__ == "__main__":
    test_aurelius_direct_reply_and_tts()
    test_aurelius_status_uses_system_version()
    test_aurelius_does_not_resolve_provider_or_models()
    test_aurelius_voice_soft_fails_without_adapter()
    print("test_aurelius_runtime PASS")
