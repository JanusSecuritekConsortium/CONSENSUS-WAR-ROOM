from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assistant.aurelius_runtime import AureliusRuntime
from core.models import FinalVerdict, TribunalResult
from integrations.msty_claw.aurelius_hooks import announce_calendar_event
from voice.aurelius_voice import (
    AureliusVoice,
    GLADOS_SPEAK_TEST_LINE,
    RVC_TEST_LINE,
    SPEAK_TEST_LINE,
    _build_arg_parser,
    build_consensus_speech_event,
)
from voice.voice_profiles import get_voice_profile
from voice.stress_texts import list_stress_keys, load_stress_text
from voice.speech_events import SpeechEvent, SpeechEventType, consensus_event_type


class DummyTTS:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def synthesize(self, text: str):
        self.lines.append(text)

        class Result:
            ok = True
            audio_path = "spoken.wav"
            mode = "dummy"
            metadata = {}

        return Result()


class DummyAnnouncer:
    def __init__(self) -> None:
        self.events: list[SpeechEvent] = []

    def announce(self, event: SpeechEvent):
        self.events.append(event)

        class Result:
            text = event.text
            spoken = True
            audio_path = "calendar.wav"
            metadata = {}

        return Result()


def test_consensus_event_type_maps_final_verdicts() -> None:
    assert consensus_event_type(FinalVerdict.APPROVED) == SpeechEventType.CONSENSUS_APPROVED
    assert consensus_event_type(FinalVerdict.APPROVE) == SpeechEventType.CONSENSUS_APPROVED
    assert consensus_event_type(FinalVerdict.DENIED) == SpeechEventType.CONSENSUS_DENIED
    assert consensus_event_type(FinalVerdict.NO_CONSENSUS) == SpeechEventType.CONSENSUS_NO_CONSENSUS
    assert consensus_event_type(FinalVerdict.CAUTION) == SpeechEventType.CONSENSUS_CAUTION
    assert consensus_event_type(FinalVerdict.ESCALATE) == SpeechEventType.CONSENSUS_ESCALATE
    assert consensus_event_type(FinalVerdict.DEADLOCK) == SpeechEventType.CONSENSUS_DEADLOCK
    assert consensus_event_type("ERROR") == SpeechEventType.CONSENSUS_DEADLOCK


def test_aurelius_voice_formats_consensus_without_direct_audio() -> None:
    tts = DummyTTS()
    voice = AureliusVoice(enabled=True, tts_adapter=tts)
    result = voice.speak(build_consensus_speech_event(FinalVerdict.APPROVED, 0.82))
    assert result.ok is True
    assert result.mode == "dummy"
    assert tts.lines == ["Consensus verdict: approved. Confidence level: 82%."]


def test_aurelius_runtime_announces_consensus_result() -> None:
    tts = DummyTTS()
    runtime = AureliusRuntime(tts_adapter=tts, voice_adapter=None)
    tribunal_result = TribunalResult(
        query="ship it",
        verdict=FinalVerdict.DEADLOCK,
        confidence=0.34,
        reason="No quorum.",
        votes={},
        vote_distribution={},
        quorum_met=False,
        review_triggers=[],
        session_id="speech-test",
        theme="military",
    )
    result = runtime.announce_consensus_verdict(tribunal_result)
    assert result.spoken is True
    assert tts.lines == ["Consensus deadlock. Manual intervention required. Confidence level: 34%."]


def test_msty_claw_calendar_hook_emits_aurelius_event() -> None:
    announcer = DummyAnnouncer()
    announce_calendar_event("created", "Dentist", "09:30", announcer=announcer)
    assert len(announcer.events) == 1
    event = announcer.events[0]
    assert event.event_type == SpeechEventType.APPOINTMENT_CREATED
    assert event.source == "MSTY_CLAW_CALENDAR"
    assert event.text == "Dentist. Scheduled for 09:30."


def test_aurelius_cli_exposes_dry_and_speak_tests() -> None:
    parser = _build_arg_parser()
    help_text = parser.format_help()
    option_help = {
        option
        for action in parser._actions
        for option in action.option_strings
    }
    assert "--test" in help_text
    assert "--speak-test" in help_text
    assert "--glados-speak-test" in help_text
    assert "--aurelius-rvc-test" in help_text
    assert "--aurelius-rvc-save-only" in help_text
    assert "--glados-rvc-save-only" in help_text
    assert "--aurelius-stress" in help_text
    assert "--glados-stress" in help_text
    assert "--stress-save-only" in help_text
    assert "--list-sapi-voices" in help_text
    assert {
        "--test",
        "--speak-test",
        "--glados-speak-test",
        "--aurelius-rvc-test",
        "--aurelius-rvc-save-only",
        "--glados-rvc-save-only",
        "--aurelius-stress",
        "--glados-stress",
        "--stress-save-only",
        "--list-sapi-voices",
    } <= option_help
    assert "dry-run consensus speech event" in help_text
    assert "real TTS backend smoke test" in help_text
    assert "ARBITER GLaDOS voice smoke test" in help_text
    assert "AURELIUS Documentary Narrator RVC" in help_text
    assert "AURELIUS RVC WAV without playback" in help_text
    assert "ARBITER_GLADOS RVC WAV without playback" in help_text
    assert "AURELIUS long-form stress fixture" in help_text
    assert "ARBITER_GLADOS long-form stress fixture" in help_text
    assert "Windows SAPI voices" in help_text
    assert SPEAK_TEST_LINE == "AURELIUS voice route operational."
    assert GLADOS_SPEAK_TEST_LINE == "The tribunal has reached a verdict."
    assert RVC_TEST_LINE == "AURELIUS route operational."


def test_voice_profiles_load_identity_layer_config() -> None:
    aurelius = get_voice_profile("AURELIUS")
    glados = get_voice_profile("ARBITER_GLADOS")
    assert aurelius.backend == "rvc"
    assert aurelius.voice == "aurelius"
    assert aurelius.settings["display_name"] == "AURELIUS"
    assert aurelius.settings["base_tts"] == "windows_sapi"
    assert aurelius.settings["base_voice_name"] == ["Microsoft George", "Microsoft Ryan", "Microsoft David"]
    assert aurelius.settings["base_voice_gender"] == "Male"
    assert aurelius.settings["base_voice_language"] == "en-GB"
    assert aurelius.settings["transpose"] == 2
    assert aurelius.settings["index_rate"] == 0.78
    assert aurelius.settings["protect"] == 0.4
    assert aurelius.settings["filter_radius"] == 3
    assert aurelius.settings["rvc_model_name"] == "aurelius.pth"
    assert aurelius.settings["rvc_python"].endswith("rvc_env/Scripts/python.exe")
    assert aurelius.settings["rvc_env"]["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] == "1"
    assert aurelius.fallback == "windows_sapi"
    assert glados.backend == "rvc"
    assert glados.voice == "glados"
    assert glados.settings["display_name"] == "ARBITER"
    assert glados.settings["base_voice_name"] == ["Microsoft Zira", "Microsoft Hazel"]
    assert glados.settings["base_voice_gender"] == "Female"
    assert glados.settings["base_voice_language"] == "en-US,en-GB"
    assert glados.settings["transpose"] == -3
    assert glados.settings["index_rate"] == 0.9
    assert glados.settings["protect"] == 0.05
    assert glados.settings["filter_radius"] == 7
    assert glados.settings["rvc_model_name"] == "arbiter_glados.pth"
    assert glados.settings["rvc_python"].endswith("rvc_env/Scripts/python.exe")


def test_voice_stress_fixtures_are_available() -> None:
    assert list_stress_keys("AURELIUS") == [
        "assistant_briefing",
        "calm_warning_notification",
        "long_documentary_cadence",
    ]
    assert list_stress_keys("ARBITER_GLADOS") == [
        "cold_synthetic_deadlock",
        "portal_style_cadence",
        "tribunal_verdict",
    ]
    assert "operational schedule" in load_stress_text("AURELIUS", "assistant_briefing")
    assert "Consensus deadlock detected" in load_stress_text("ARBITER_GLADOS", "cold_synthetic_deadlock")


if __name__ == "__main__":
    test_consensus_event_type_maps_final_verdicts()
    test_aurelius_voice_formats_consensus_without_direct_audio()
    test_aurelius_runtime_announces_consensus_result()
    test_msty_claw_calendar_hook_emits_aurelius_event()
    test_aurelius_cli_exposes_dry_and_speak_tests()
    test_voice_profiles_load_identity_layer_config()
    test_voice_stress_fixtures_are_available()
    print("test_aurelius_voice_events PASS")
