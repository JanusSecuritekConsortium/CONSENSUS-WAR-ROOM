from __future__ import annotations

import math
import os
import wave
from array import array
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class WavQualityReport:
    path: str
    channels: int
    sample_width: int
    sample_rate: int
    frames: int
    duration_seconds: float
    peak_dbfs: float
    rms_dbfs: float
    clipped_percent: float
    silent_windows_percent: float
    baseline_ok: bool

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def analyze_wav(path: Path | str, *, silence_dbfs: float = -50.0, window_ms: int = 20) -> WavQualityReport:
    target = Path(path)
    with wave.open(str(target), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        frame_count = source.getnframes()
        raw = source.readframes(frame_count)
    if sample_width != 2:
        raise ValueError(f"only 16-bit PCM WAV is supported: {target}")

    samples = array("h")
    samples.frombytes(raw)
    if channels > 1:
        mono = array("h")
        for index in range(0, len(samples), channels):
            mono.append(round(sum(samples[index : index + channels]) / channels))
        samples = mono
    absolute = [abs(value) for value in samples]
    peak = max(absolute, default=0) / 32768.0
    rms = math.sqrt(sum(value * value for value in samples) / max(1, len(samples))) / 32768.0
    clipped = sum(value >= 32767 for value in absolute) / max(1, len(absolute)) * 100.0

    window_frames = max(1, round(sample_rate * window_ms / 1000))
    threshold = 10 ** (silence_dbfs / 20.0)
    silent = 0
    window_count = 0
    for start in range(0, len(samples), window_frames):
        block = samples[start : start + window_frames]
        if not block:
            continue
        block_rms = math.sqrt(sum(value * value for value in block) / len(block)) / 32768.0
        silent += block_rms < threshold
        window_count += 1

    duration = len(samples) / sample_rate if sample_rate else 0.0
    silent_percent = silent / max(1, window_count) * 100.0
    baseline_ok = (
        sample_rate >= 22_050
        and channels in {1, 2}
        and duration >= 0.25
        and peak > 0.0
        and clipped <= 0.1
        and silent_percent <= 80.0
    )
    return WavQualityReport(
        path=str(target),
        channels=channels,
        sample_width=sample_width,
        sample_rate=sample_rate,
        frames=frame_count,
        duration_seconds=round(duration, 3),
        peak_dbfs=round(_dbfs(peak), 2),
        rms_dbfs=round(_dbfs(rms), 2),
        clipped_percent=round(clipped, 4),
        silent_windows_percent=round(silent_percent, 2),
        baseline_ok=baseline_ok,
    )


def polish_wav(
    path: Path | str,
    *,
    silence_dbfs: float = -45.0,
    padding_ms: int = 60,
    target_peak_dbfs: float = -1.5,
    max_gain_db: float = 6.0,
) -> WavQualityReport:
    """Trim quiet edges and apply bounded peak normalization to a 16-bit PCM WAV."""
    target = Path(path)
    with wave.open(str(target), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        compression = source.getcomptype()
        raw = source.readframes(source.getnframes())
    if sample_width != 2 or compression != "NONE":
        raise ValueError(f"only uncompressed 16-bit PCM WAV is supported: {target}")

    samples = array("h")
    samples.frombytes(raw)
    total_frames = len(samples) // max(1, channels)
    window_frames = max(1, round(sample_rate * 0.01))
    threshold = 32768.0 * 10 ** (silence_dbfs / 20.0)
    active_windows: list[tuple[int, int]] = []
    for start_frame in range(0, total_frames, window_frames):
        end_frame = min(total_frames, start_frame + window_frames)
        block = samples[start_frame * channels : end_frame * channels]
        if not block:
            continue
        rms = math.sqrt(sum(value * value for value in block) / len(block))
        if rms >= threshold:
            active_windows.append((start_frame, end_frame))
    if not active_windows:
        raise ValueError(f"cannot polish silent WAV: {target}")

    padding_frames = round(sample_rate * padding_ms / 1000)
    first_frame = max(0, active_windows[0][0] - padding_frames)
    last_frame = min(total_frames, active_windows[-1][1] + padding_frames)
    polished = samples[first_frame * channels : last_frame * channels]

    peak = max((abs(value) for value in polished), default=0)
    if peak:
        desired_peak = 32767.0 * 10 ** (target_peak_dbfs / 20.0)
        gain = min(desired_peak / peak, 10 ** (max_gain_db / 20.0))
        if gain > 1.0:
            polished = array("h", (max(-32768, min(32767, round(value * gain))) for value in polished))

    temporary = target.with_name(f"{target.stem}.polished{target.suffix}")
    try:
        with wave.open(str(temporary), "wb") as output:
            output.setnchannels(channels)
            output.setsampwidth(sample_width)
            output.setframerate(sample_rate)
            output.writeframes(polished.tobytes())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return analyze_wav(target)


def _dbfs(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-12))


__all__ = ["WavQualityReport", "analyze_wav", "polish_wav"]
