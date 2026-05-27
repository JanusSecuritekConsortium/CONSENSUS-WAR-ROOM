from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol

try:
    from .speech_events import SpeechEvent, SpeechEventType, consensus_event_type
except ImportError:
    from voice.speech_events import SpeechEvent, SpeechEventType, consensus_event_type


class TTSAdapter(Protocol):
    def synthesize(self, text: str) -> Any:
        ...


@dataclass
class VoiceSpeakResult:
    ok: bool
    text: str = ""
    mode: str = "disabled"
    audio_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AureliusVoice:
    """AURELIUS voice event router; ARBITER and calendar modules emit events."""

    def __init__(
        self,
        enabled: bool = True,
        rate: int = 145,
        volume: float = 0.9,
        tts_adapter: Optional[TTSAdapter] = None,
    ) -> None:
        self.enabled = enabled
        self.rate = rate
        self.volume = volume
        self.tts_adapter = tts_adapter
        self.engine: Any = None
        self.engine_backend: Optional[str] = None

    def initialize(self) -> None:
        if not self.enabled or self.tts_adapter is not None:
            return
        try:
            import pyttsx3  # type: ignore
        except Exception:
            if os.name == "nt":
                self.engine_backend = "windows_sapi"
                return
            raise

        self.engine = pyttsx3.init()
        self.engine_backend = "pyttsx3"
        self.engine.setProperty("rate", self.rate)
        self.engine.setProperty("volume", self.volume)
        voices = self.engine.getProperty("voices")
        for voice in voices:
            name = str(getattr(voice, "name", "")).lower()
            if "david" in name or "george" in name or "male" in name:
                self.engine.setProperty("voice", voice.id)
                break

    def speak(self, event: SpeechEvent) -> VoiceSpeakResult:
        line = self.format_line(event)
        if not self.enabled:
            return VoiceSpeakResult(ok=True, text=line, mode="disabled")
        if self.tts_adapter is not None:
            return self._synthesize(line)
        try:
            if self.engine is None:
                self.initialize()
            if self.engine_backend == "windows_sapi":
                return self._speak_with_windows_sapi(line)
            self.engine.say(line)
            self.engine.runAndWait()
        except Exception as exc:
            return VoiceSpeakResult(ok=False, text=line, mode="pyttsx3", metadata={"error": str(exc)})
        return VoiceSpeakResult(ok=True, text=line, mode=self.engine_backend or "pyttsx3")

    def _synthesize(self, line: str) -> VoiceSpeakResult:
        try:
            rendered = self.tts_adapter.synthesize(line)
        except Exception as exc:
            return VoiceSpeakResult(ok=False, text=line, mode="adapter", metadata={"error": str(exc)})
        ok = bool(getattr(rendered, "ok", False))
        return VoiceSpeakResult(
            ok=ok,
            text=line,
            mode=str(getattr(rendered, "mode", "adapter")),
            audio_path=getattr(rendered, "audio_path", None),
            metadata=getattr(rendered, "metadata", {}) or {},
        )

    def _speak_with_windows_sapi(self, line: str) -> VoiceSpeakResult:
        escaped = line.replace("'", "''")
        volume = max(0, min(100, int(self.volume * 100)))
        rate = max(-10, min(10, int((self.rate - 145) / 10)))
        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speaker.Volume = {volume}; "
            f"$speaker.Rate = {rate}; "
            f"$speaker.Speak('{escaped}'); "
            "$speaker.Dispose()"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout or "Windows SAPI playback failed").strip()
            return VoiceSpeakResult(ok=False, text=line, mode="windows_sapi", metadata={"error": error})
        return VoiceSpeakResult(ok=True, text=line, mode="windows_sapi")

    def format_line(self, event: SpeechEvent) -> str:
        if event.event_type == SpeechEventType.APPOINTMENT_CREATED:
            return f"Acknowledged. Appointment registered. {event.text}"
        if event.event_type == SpeechEventType.APPOINTMENT_REMINDER:
            return f"Reminder. {event.text}"
        if event.event_type == SpeechEventType.APPOINTMENT_SUMMARY:
            return f"Calendar summary. {event.text}"
        if event.event_type == SpeechEventType.CONSENSUS_APPROVED:
            return f"Consensus verdict: approved. {event.text}"
        if event.event_type == SpeechEventType.CONSENSUS_DENIED:
            return f"Consensus verdict: denied. {event.text}"
        if event.event_type == SpeechEventType.CONSENSUS_CONDITIONAL_APPROVAL:
            return f"Consensus verdict: conditional approval. {event.text}"
        if event.event_type == SpeechEventType.CONSENSUS_HUMAN_REVIEW_REQUIRED:
            return f"Consensus verdict: human review required. {event.text}"
        if event.event_type == SpeechEventType.CONSENSUS_ABSTAINED:
            return f"The tribunal abstains. {event.text}"
        if event.event_type == SpeechEventType.CONSENSUS_NO_CONSENSUS:
            return f"No consensus. The tribunal is unresolved. {event.text}"
        if event.event_type == SpeechEventType.CONSENSUS_CAUTION:
            return f"Caution. Critical risk prevents clean consensus. {event.text}"
        if event.event_type == SpeechEventType.CONSENSUS_ESCALATE:
            return f"Escalate. Human authority required. {event.text}"
        if event.event_type == SpeechEventType.CONSENSUS_DEADLOCK:
            return f"Consensus deadlock. Manual intervention required. {event.text}"
        return event.text


SPEAK_TEST_LINE = "AURELIUS voice route operational."
GLADOS_SPEAK_TEST_LINE = "The tribunal has reached a verdict."
try:
    from .rvc_adapter import RVC_TEST_LINE
except ImportError:
    try:
        from voice.rvc_adapter import RVC_TEST_LINE
    except ImportError:
        RVC_TEST_LINE = "AURELIUS documentary narrator route operational."


def build_consensus_speech_event(consensus: object, confidence: float, text: str = "") -> SpeechEvent:
    line = text.strip() or f"Confidence level: {confidence:.0%}."
    return SpeechEvent(
        event_type=consensus_event_type(consensus),
        text=line,
        priority=8,
        source="ARBITER",
        metadata={"confidence": confidence, "verdict": str(getattr(consensus, "value", consensus))},
    )


def announce_consensus_verdict(
    consensus: object,
    confidence: float,
    text: str = "",
    voice: Optional[AureliusVoice] = None,
) -> VoiceSpeakResult:
    announcer = voice or AureliusVoice(enabled=True)
    return announcer.speak(build_consensus_speech_event(consensus, confidence, text))


def _run_test() -> int:
    event = build_consensus_speech_event("APPROVED", 0.82)
    result = AureliusVoice(enabled=False).speak(event)
    print(result.text)
    return 0 if result.ok else 1


def _run_speak_test() -> int:
    result = AureliusVoice(enabled=True).speak(
        SpeechEvent(
            event_type=SpeechEventType.SYSTEM_NOTICE,
            text=SPEAK_TEST_LINE,
            priority=9,
            source="AURELIUS_CLI",
        )
    )
    if result.ok:
        print("AURELIUS speak-test completed.")
        return 0
    error = result.metadata.get("error", "unknown playback error")
    print(f"AURELIUS speak-test failed: {error}")
    return 1


def _run_glados_speak_test() -> int:
    try:
        try:
            from .glados_adapter import GladosAdapter
        except ImportError:
            from voice.glados_adapter import GladosAdapter

        result = GladosAdapter().speak(GLADOS_SPEAK_TEST_LINE)
    except Exception as exc:
        print(f"GLaDOS speak-test failed: {exc}")
        return 1
    if result.ok:
        if result.mode == "glados_tts":
            print("GLaDOS speak-test completed.")
        elif result.mode == "rvc":
            print("GLaDOS speak-test completed via rvc.")
        else:
            print(f"GLaDOS speak-test completed via {result.mode} fallback.")
        return 0
    error = result.metadata.get("error", "unknown playback error")
    print(f"GLaDOS speak-test failed: {error}")
    return 1


def _run_aurelius_rvc_test() -> int:
    try:
        try:
            from .rvc_adapter import RVCAdapter
        except ImportError:
            from voice.rvc_adapter import RVCAdapter

        result = RVCAdapter().speak(RVC_TEST_LINE)
    except Exception as exc:
        print(f"AURELIUS RVC test failed: {exc}")
        return 1
    if result.ok:
        if result.mode == "rvc":
            print("AURELIUS RVC test completed via rvc.")
        else:
            print(f"AURELIUS RVC test completed via {result.mode} fallback.")
        return 0
    error = result.metadata.get("error", "unknown RVC error")
    print(f"AURELIUS RVC test failed: {error}")
    return 1


def _run_aurelius_rvc_save_only() -> int:
    try:
        try:
            from .rvc_adapter import RVCAdapter
        except ImportError:
            from voice.rvc_adapter import RVCAdapter

        result = RVCAdapter().save_only(RVC_TEST_LINE)
    except Exception as exc:
        print(f"AURELIUS RVC save-only failed: {exc}")
        return 1
    if result.ok:
        print(f"AURELIUS RVC save-only completed: {result.audio_path}")
        return 0
    error = result.metadata.get("error", "unknown RVC error")
    print(f"AURELIUS RVC save-only failed: {error}")
    return 1


def _run_glados_rvc_save_only() -> int:
    try:
        try:
            from .rvc_adapter import RVCAdapter
            from .voice_profiles import get_voice_profile
        except ImportError:
            from voice.rvc_adapter import RVCAdapter
            from voice.voice_profiles import get_voice_profile

        result = RVCAdapter(profile=get_voice_profile("ARBITER_GLADOS")).save_only(GLADOS_SPEAK_TEST_LINE)
    except Exception as exc:
        print(f"GLaDOS RVC save-only failed: {exc}")
        return 1
    if result.ok:
        print(f"GLaDOS RVC save-only completed: {result.audio_path}")
        return 0
    error = result.metadata.get("error", "unknown RVC error")
    print(f"GLaDOS RVC save-only failed: {error}")
    return 1


def _run_stress_test(profile: str, key: str, save_only: bool) -> int:
    try:
        try:
            from .rvc_adapter import RVCAdapter
            from .stress_texts import list_stress_keys, load_stress_text
            from .voice_profiles import get_voice_profile
        except ImportError:
            from voice.rvc_adapter import RVCAdapter
            from voice.stress_texts import list_stress_keys, load_stress_text
            from voice.voice_profiles import get_voice_profile

        if key == "list":
            for item in list_stress_keys(profile):
                print(item)
            return 0
        text = load_stress_text(profile, key)
        adapter = RVCAdapter(profile=get_voice_profile(profile))
        result = adapter.save_only(text) if save_only else adapter.speak(text)
    except Exception as exc:
        print(f"{profile} stress test failed: {exc}")
        return 1
    if result.ok:
        action = "save-only" if save_only else "playback"
        print(f"{profile} stress test {action} completed: {result.audio_path}")
        return 0
    error = result.metadata.get("error", "unknown stress test error")
    print(f"{profile} stress test failed: {error}")
    return 1


def _run_list_sapi_voices() -> int:
    try:
        try:
            from .tts_backends import format_sapi_voices
        except ImportError:
            from voice.tts_backends import format_sapi_voices

        print(format_sapi_voices())
    except Exception as exc:
        print(f"Failed to list Windows SAPI voices: {exc}")
        return 1
    return 0


def _build_arg_parser():
    import argparse

    parser = argparse.ArgumentParser(description="AURELIUS voice event router")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--test", action="store_true", help="format a dry-run consensus speech event")
    group.add_argument("--speak-test", action="store_true", help="play a real TTS backend smoke test")
    group.add_argument("--glados-speak-test", action="store_true", help="play the ARBITER GLaDOS voice smoke test")
    group.add_argument("--aurelius-rvc-test", action="store_true", help="play the optional AURELIUS Documentary Narrator RVC route")
    group.add_argument("--aurelius-rvc-save-only", action="store_true", help="generate the AURELIUS RVC WAV without playback")
    group.add_argument("--glados-rvc-save-only", action="store_true", help="generate the ARBITER_GLADOS RVC WAV without playback")
    parser.add_argument("--aurelius-stress", metavar="KEY", help="run or list an AURELIUS long-form stress fixture")
    parser.add_argument("--glados-stress", metavar="KEY", help="run or list an ARBITER_GLADOS long-form stress fixture")
    parser.add_argument("--stress-save-only", action="store_true", help="generate stress-test WAV without playback")
    parser.add_argument("--list-sapi-voices", action="store_true", help="list Windows SAPI voices available for base WAV generation")
    return parser


if __name__ == "__main__":
    parser = _build_arg_parser()
    args = parser.parse_args()
    if args.test:
        raise SystemExit(_run_test())
    if args.speak_test:
        raise SystemExit(_run_speak_test())
    if args.glados_speak_test:
        raise SystemExit(_run_glados_speak_test())
    if args.aurelius_rvc_test:
        raise SystemExit(_run_aurelius_rvc_test())
    if args.aurelius_rvc_save_only:
        raise SystemExit(_run_aurelius_rvc_save_only())
    if args.glados_rvc_save_only:
        raise SystemExit(_run_glados_rvc_save_only())
    if args.aurelius_stress:
        raise SystemExit(_run_stress_test("AURELIUS", args.aurelius_stress, args.stress_save_only))
    if args.glados_stress:
        raise SystemExit(_run_stress_test("ARBITER_GLADOS", args.glados_stress, args.stress_save_only))
    if args.list_sapi_voices:
        raise SystemExit(_run_list_sapi_voices())
    parser.print_help()
