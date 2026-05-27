from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol

from config.version import SYSTEM_VERSION
from core.logging import log_event
from core.paths import ARBITER_DIR
from voice.aurelius_voice import AureliusVoice, build_consensus_speech_event
from voice.speech_events import SpeechEvent


class TTSAdapter(Protocol):
    def synthesize(self, text: str) -> Any:
        ...


class VoiceAdapter(Protocol):
    def listen_once(self) -> Any:
        ...


@dataclass
class AureliusResult:
    text: str
    spoken: bool = False
    audio_path: Optional[str] = None
    routed_to_consensus: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


ConsensusHandler = Callable[[str], Any]


class AureliusRuntime:
    """Operator assistant runtime; provider/model truth stays in the consensus runtime."""

    def __init__(
        self,
        tts_adapter: Optional[TTSAdapter] = None,
        voice_adapter: Optional[VoiceAdapter] = None,
        consensus_handler: Optional[ConsensusHandler] = None,
        persona_path: Optional[Path] = None,
    ) -> None:
        self.tts_adapter = tts_adapter
        self.voice_adapter = voice_adapter
        self.consensus_handler = consensus_handler
        self.persona_path = persona_path or Path(__file__).with_name("aurelius_persona.yaml")
        self.voice_loop_enabled = False

    def set_voice_loop(self, enabled: bool) -> None:
        self.voice_loop_enabled = bool(enabled)
        log_event("aurelius_voice_loop", {"enabled": self.voice_loop_enabled})

    def status(self) -> Dict[str, Any]:
        return {
            "version": SYSTEM_VERSION,
            "runtime": "AURELIUS",
            "voice_loop_enabled": self.voice_loop_enabled,
            "tts_available": self.tts_adapter is not None,
            "voice_adapter_available": self.voice_adapter is not None,
            "consensus_route_available": self.consensus_handler is not None,
            "persona_path": str(self.persona_path),
        }

    def handle_text(
        self,
        text: str,
        speak: bool = False,
        route_to_consensus: bool = False,
    ) -> AureliusResult:
        prompt = text.strip()
        if not prompt:
            return AureliusResult(
                text="A.U.R.E.L.I.U.S. received no operator input.",
                metadata={"error": "empty_input"},
            )

        routed_payload: Any = None
        routed = False
        if route_to_consensus:
            if self.consensus_handler is None:
                return AureliusResult(
                    text="A.U.R.E.L.I.U.S. cannot route to CONSENSUS: no consensus handler is attached.",
                    metadata={"error": "consensus_handler_missing"},
                )
            routed_payload = self.consensus_handler(prompt)
            routed = True

        response = self._compose_response(prompt, routed_payload)
        spoken = False
        audio_path: Optional[str] = None
        metadata: Dict[str, Any] = {}
        if speak:
            if self.tts_adapter is None:
                metadata["tts"] = "unavailable"
            else:
                try:
                    rendered = self.tts_adapter.synthesize(response)
                    spoken = bool(getattr(rendered, "ok", False))
                    audio_path = getattr(rendered, "audio_path", None)
                    metadata["tts"] = "rendered" if spoken else "failed"
                except Exception as exc:
                    metadata["tts"] = "failed"
                    metadata["tts_error"] = str(exc)

        result = AureliusResult(
            text=response,
            spoken=spoken,
            audio_path=audio_path,
            routed_to_consensus=routed,
            metadata=metadata,
        )
        log_event(
            "aurelius_text_handled",
            {
                "routed_to_consensus": result.routed_to_consensus,
                "spoken": result.spoken,
                "has_error": "error" in result.metadata,
            },
        )
        return result

    def announce(self, event: SpeechEvent) -> AureliusResult:
        if self.tts_adapter is None:
            formatted = AureliusVoice(enabled=False).speak(event)
            return AureliusResult(
                text=formatted.text,
                spoken=False,
                metadata={"tts": "unavailable", "event_type": event.event_type.value},
            )
        rendered = AureliusVoice(enabled=True, tts_adapter=self.tts_adapter).speak(event)
        result = AureliusResult(
            text=rendered.text,
            spoken=rendered.ok,
            audio_path=rendered.audio_path,
            metadata={
                "tts": "rendered" if rendered.ok else "failed",
                "event_type": event.event_type.value,
                "mode": rendered.mode,
                **rendered.metadata,
            },
        )
        log_event(
            "aurelius_speech_event",
            {
                "event_type": event.event_type.value,
                "source": event.source,
                "spoken": result.spoken,
                "mode": result.metadata.get("mode"),
            },
        )
        return result

    def announce_consensus_verdict(self, result: Any) -> AureliusResult:
        confidence = float(getattr(result, "confidence", 0.0) or 0.0)
        verdict = getattr(result, "verdict", "ERROR")
        event = build_consensus_speech_event(
            verdict,
            confidence,
            f"Confidence level: {confidence:.0%}.",
        )
        return self.announce(event)

    def poll_voice_once(self, speak: bool = True, route_to_consensus: bool = False) -> AureliusResult:
        if self.voice_adapter is None:
            return AureliusResult(
                text="A.U.R.E.L.I.U.S. voice input unavailable.",
                metadata={"error": "voice_adapter_missing"},
            )
        try:
            heard = self.voice_adapter.listen_once()
        except Exception as exc:
            return AureliusResult(
                text=f"A.U.R.E.L.I.U.S. voice input failed: {exc}",
                metadata={"error": "voice_input_failed"},
            )
        text = str(getattr(heard, "text", heard) or "").strip()
        if not text:
            return AureliusResult(
                text="A.U.R.E.L.I.U.S. heard no usable operator input.",
                metadata={"error": "empty_voice_input"},
            )
        return self.handle_text(text, speak=speak, route_to_consensus=route_to_consensus)

    def _compose_response(self, prompt: str, routed_payload: Any = None) -> str:
        if routed_payload is not None:
            return "A.U.R.E.L.I.U.S. routed the operator request to CONSENSUS and received a tribunal response."
        return f"A.U.R.E.L.I.U.S. operator channel ready. Input acknowledged: {prompt}"


_RUNTIME: Optional[AureliusRuntime] = None


def _default_manifest_path() -> Path:
    path = ARBITER_DIR / "aurelius"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"aurelius_tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def get_aurelius_runtime() -> AureliusRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        from voice.attenborough_tts_adapter import AttenboroughTTSAdapter
        from voice.riko_adapter import RikoVoiceAdapter

        _RUNTIME = AureliusRuntime(
            tts_adapter=AttenboroughTTSAdapter(manifest_factory=_default_manifest_path),
            voice_adapter=RikoVoiceAdapter(),
        )
    return _RUNTIME


__all__ = ["AureliusRuntime", "AureliusResult", "get_aurelius_runtime"]
