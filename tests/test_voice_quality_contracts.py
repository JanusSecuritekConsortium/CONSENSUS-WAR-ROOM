from __future__ import annotations

import sys
import tempfile
import wave
import math
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assistant import aurelius_runtime
from voice.attenborough_tts_adapter import AttenboroughTTSAdapter, TTSRenderResult
from voice.audio_quality import analyze_wav, polish_wav
from voice.aurelius_adapter import AureliusAdapter
from voice.glados_adapter import GladosAdapter
from voice.rvc_adapter import RVCAdapter
from voice.text_normalization import normalize_for_speech, split_speech_text
from voice.voice_profiles import get_voice_profile


class UnavailableLegacyAdapter(AttenboroughTTSAdapter):
    def _synthesize_with_pyttsx3(self, text: str) -> TTSRenderResult:
        return TTSRenderResult(ok=False, mode="pyttsx3", metadata={"error": "unavailable"})


def test_operator_text_is_normalized_for_both_voice_routes() -> None:
    source = "A.U.R.E.L.I.U.S. reports CONSENSUS_SYSTEM proposal A-17 at 14:05 with 72.5% confidence via RVC API."
    assert normalize_for_speech(source) == (
        "Aurelius reports Consensus System proposal A seventeen at fourteen oh five "
        "with seventy two point five percent confidence via R V C A P I."
    )


def test_long_speech_is_split_without_losing_words() -> None:
    source = "First sentence contains a compact status update. Second sentence contains the detailed operator explanation."
    normalized = normalize_for_speech(source)
    chunks = split_speech_text(source, max_chars=80)
    assert len(chunks) == 2
    assert " ".join(chunks) == normalized
    assert all(len(chunk) <= 80 for chunk in chunks)


def test_aurelius_runtime_uses_the_rvc_backed_adapter() -> None:
    original = aurelius_runtime._RUNTIME
    try:
        aurelius_runtime._RUNTIME = None
        runtime = aurelius_runtime.get_aurelius_runtime()
        assert isinstance(runtime.tts_adapter, AureliusAdapter)
        assert runtime.tts_adapter.profile.backend == "rvc"
    finally:
        aurelius_runtime._RUNTIME = original


def test_legacy_manifest_is_not_reported_as_spoken_audio() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        adapter = UnavailableLegacyAdapter(
            output_dir=root,
            manifest_factory=lambda: root / "diagnostic.json",
        )
        result = adapter.synthesize("Status at 09:30.")
        assert result.ok is False
        assert result.mode == "dry_run"
        assert result.metadata["error"] == "audio_backend_unavailable"
        assert Path(result.audio_path or "").suffix == ".json"


def test_glados_primary_and_fallback_backends_are_explicit() -> None:
    profile = get_voice_profile("ARBITER_GLADOS")
    adapter = GladosAdapter(profile=profile)
    assert profile.backend == "glados_tts"
    assert profile.fallback == "rvc"
    assert adapter.backend == "glados_tts"
    assert adapter.rvc is None
    assert adapter.rvc_fallback is not None


def test_rvc_chunk_concatenation_preserves_wav_format() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        first = root / "first.wav"
        second = root / "second.wav"
        target = root / "joined.wav"
        _write_silent_wav(first, frames=800)
        _write_silent_wav(second, frames=1_200)
        RVCAdapter._concatenate_wavs([first, second], target)
        with wave.open(str(target), "rb") as joined:
            assert joined.getframerate() == 40_000
            assert joined.getnchannels() == 1
            assert joined.getsampwidth() == 2
            assert joined.getnframes() == 2_000


def test_wav_quality_gate_accepts_clean_pcm_and_rejects_silence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        voiced = root / "voiced.wav"
        silent = root / "silent.wav"
        _write_tone_wav(voiced)
        _write_silent_wav(silent, frames=40_000)
        assert analyze_wav(voiced).baseline_ok is True
        assert analyze_wav(silent).baseline_ok is False


def test_wav_polishing_trims_edges_and_normalizes_quiet_audio() -> None:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "padded.wav"
        silence = array("h", [0]) * 20_000
        tone = array("h", (round(16_000 * math.sin(2 * math.pi * 220 * index / 40_000)) for index in range(40_000)))
        with wave.open(str(target), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(40_000)
            output.writeframes((silence + tone + silence).tobytes())
        report = polish_wav(target)
        assert 1.1 <= report.duration_seconds <= 1.14
        assert -1.6 <= report.peak_dbfs <= -1.4
        assert report.clipped_percent == 0.0


def _write_silent_wav(path: Path, *, frames: int) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(40_000)
        output.writeframes(b"\x00\x00" * frames)


def _write_tone_wav(path: Path) -> None:
    samples = array("h", (round(8_000 * math.sin(2 * math.pi * 220 * index / 40_000)) for index in range(40_000)))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(40_000)
        output.writeframes(samples.tobytes())


if __name__ == "__main__":
    test_operator_text_is_normalized_for_both_voice_routes()
    test_long_speech_is_split_without_losing_words()
    test_aurelius_runtime_uses_the_rvc_backed_adapter()
    test_legacy_manifest_is_not_reported_as_spoken_audio()
    test_glados_primary_and_fallback_backends_are_explicit()
    test_rvc_chunk_concatenation_preserves_wav_format()
    test_wav_quality_gate_accepts_clean_pcm_and_rejects_silence()
    test_wav_polishing_trims_edges_and_normalizes_quiet_audio()
    print("test_voice_quality_contracts PASS")
