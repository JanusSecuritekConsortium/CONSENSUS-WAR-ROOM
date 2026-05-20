from __future__ import annotations

from typing import Any

__all__ = [
    "AttenboroughTTSAdapter",
    "AureliusVoice",
    "AureliusAdapter",
    "GladosAdapter",
    "SpeechEvent",
    "SpeechEventType",
    "TTSBackendResult",
    "TTSRenderResult",
    "RikoVoiceAdapter",
    "RVCAdapter",
    "VoiceProfile",
    "VoiceInputResult",
    "VoiceSpeakResult",
    "WindowsSAPIBackend",
]


def __getattr__(name: str) -> Any:
    if name in {"AttenboroughTTSAdapter", "TTSRenderResult"}:
        try:
            from .attenborough_tts_adapter import AttenboroughTTSAdapter, TTSRenderResult
        except ModuleNotFoundError:
            AttenboroughTTSAdapter = None  # type: ignore[assignment]
            TTSRenderResult = None  # type: ignore[assignment]
        return {
            "AttenboroughTTSAdapter": AttenboroughTTSAdapter,
            "TTSRenderResult": TTSRenderResult,
        }[name]
    if name in {"AureliusVoice", "VoiceSpeakResult"}:
        from .aurelius_voice import AureliusVoice, VoiceSpeakResult

        return {
            "AureliusVoice": AureliusVoice,
            "VoiceSpeakResult": VoiceSpeakResult,
        }[name]
    if name in {"RikoVoiceAdapter", "VoiceInputResult"}:
        from .riko_adapter import RikoVoiceAdapter, VoiceInputResult

        return {
            "RikoVoiceAdapter": RikoVoiceAdapter,
            "VoiceInputResult": VoiceInputResult,
        }[name]
    if name == "AureliusAdapter":
        from .aurelius_adapter import AureliusAdapter

        return AureliusAdapter
    if name == "GladosAdapter":
        from .glados_adapter import GladosAdapter

        return GladosAdapter
    if name == "RVCAdapter":
        from .rvc_adapter import RVCAdapter

        return RVCAdapter
    if name in {"TTSBackendResult", "WindowsSAPIBackend"}:
        from .tts_backends import TTSBackendResult, WindowsSAPIBackend

        return {
            "TTSBackendResult": TTSBackendResult,
            "WindowsSAPIBackend": WindowsSAPIBackend,
        }[name]
    if name == "VoiceProfile":
        from .voice_profiles import VoiceProfile

        return VoiceProfile
    if name in {"SpeechEvent", "SpeechEventType"}:
        from .speech_events import SpeechEvent, SpeechEventType

        return {
            "SpeechEvent": SpeechEvent,
            "SpeechEventType": SpeechEventType,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
