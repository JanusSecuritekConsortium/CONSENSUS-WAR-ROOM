from __future__ import annotations

try:
    from .rvc_adapter import RVCAdapter
    from .tts_backends import TTSBackendResult, WindowsSAPIBackend
    from .voice_profiles import VoiceProfile, get_voice_profile
except ImportError:
    from voice.rvc_adapter import RVCAdapter
    from voice.tts_backends import TTSBackendResult, WindowsSAPIBackend
    from voice.voice_profiles import VoiceProfile, get_voice_profile


class AureliusAdapter:
    """Calm British documentary narrator profile; not an exact living-person clone."""

    def __init__(self, profile: VoiceProfile | None = None) -> None:
        self.profile = profile or get_voice_profile("AURELIUS")
        if self.profile.backend == "rvc":
            self.backend = RVCAdapter(profile=self.profile)
        else:
            self.backend = WindowsSAPIBackend(rate=self.profile.rate, volume=self.profile.volume)

    def synthesize(self, text: str) -> TTSBackendResult:
        return self.backend.synthesize(text)

    def speak(self, text: str) -> TTSBackendResult:
        return self.backend.speak(text)
