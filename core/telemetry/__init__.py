from __future__ import annotations

import csv
import shutil
import subprocess
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Iterable

from core.paths import SYSTEM_ROOT


TelemetrySample = Dict[str, Any]


def _round_percent(value: Any) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _unavailable_gpu(source: str = "unavailable", reason: str = "gpu_backend_unavailable") -> Dict[str, Any]:
    return {
        "status": "unavailable",
        "source": source,
        "usage_percent": None,
        "vram_percent": None,
        "temperature_c": None,
        "reason": reason,
    }


def _gpu_from_nvidia_smi() -> Dict[str, Any]:
    if shutil.which("nvidia-smi") is None:
        raise RuntimeError("nvidia-smi not found")
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
        timeout=2,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError(completed.stderr.strip() or "nvidia-smi returned no data")
    row = next(csv.reader(completed.stdout.splitlines()))
    usage = _round_percent(row[0])
    used = _round_percent(row[1])
    total = _round_percent(row[2])
    temp = _round_percent(row[3])
    vram = round((used / total) * 100, 2) if used is not None and total else None
    return {
        "status": "ready",
        "source": "nvidia-smi",
        "usage_percent": usage,
        "vram_percent": vram,
        "temperature_c": temp,
    }


def _gpu_from_gputil() -> Dict[str, Any]:
    import GPUtil  # type: ignore

    gpus = GPUtil.getGPUs()
    if not gpus:
        raise RuntimeError("GPUtil returned no GPUs")
    gpu = gpus[0]
    usage = _round_percent(getattr(gpu, "load", 0.0) * 100)
    memory_util = getattr(gpu, "memoryUtil", None)
    if memory_util is None:
        used = getattr(gpu, "memoryUsed", None)
        total = getattr(gpu, "memoryTotal", None)
        vram = round((float(used) / float(total)) * 100, 2) if used is not None and total else None
    else:
        vram = _round_percent(float(memory_util) * 100)
    return {
        "status": "ready",
        "source": "GPUtil",
        "usage_percent": usage,
        "vram_percent": vram,
        "temperature_c": _round_percent(getattr(gpu, "temperature", None)),
    }


def collect_gpu_telemetry() -> Dict[str, Any]:
    try:
        return _gpu_from_nvidia_smi()
    except Exception as nvidia_error:
        try:
            return _gpu_from_gputil()
        except Exception as gputil_error:
            return _unavailable_gpu(reason=f"{nvidia_error}; {gputil_error}")


def collect_system_telemetry(disk_path: Path | str = SYSTEM_ROOT) -> TelemetrySample:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        import psutil  # type: ignore

        cpu_percent = _round_percent(psutil.cpu_percent(interval=None))
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(disk_path))
        sample: TelemetrySample = {
            "status": "READY",
            "degraded_reason": None,
            "timestamp": timestamp,
            "source": {"system": "psutil", "gpu": "optional"},
            "cpu": {"status": "ready", "percent": cpu_percent},
            "ram": {
                "status": "ready",
                "percent": _round_percent(memory.percent),
                "used_bytes": int(memory.used),
                "total_bytes": int(memory.total),
            },
            "disk": {
                "status": "ready",
                "percent": _round_percent(disk.percent),
                "used_bytes": int(disk.used),
                "total_bytes": int(disk.total),
            },
        }
    except ModuleNotFoundError as exc:
        reason = "psutil missing" if exc.name == "psutil" else str(exc)
        sample = {
            "status": "DEGRADED",
            "degraded_reason": reason,
            "install_hints": ["python -m pip install -e .", "python -m pip install psutil"],
            "timestamp": timestamp,
            "source": {"system": "unavailable", "gpu": "optional"},
            "cpu": {"status": "unavailable", "percent": None, "reason": reason},
            "ram": {"status": "unavailable", "percent": None, "reason": reason},
            "disk": {"status": "unavailable", "percent": None, "reason": reason},
        }
    except Exception as exc:
        sample = {
            "status": "DEGRADED",
            "degraded_reason": str(exc),
            "timestamp": timestamp,
            "source": {"system": "unavailable", "gpu": "optional"},
            "cpu": {"status": "unavailable", "percent": None, "reason": str(exc)},
            "ram": {"status": "unavailable", "percent": None, "reason": str(exc)},
            "disk": {"status": "unavailable", "percent": None, "reason": str(exc)},
        }
    gpu = collect_gpu_telemetry()
    sample["gpu"] = gpu
    sample["source"]["gpu"] = gpu.get("source", "unavailable")
    return sample


def telemetry_value(sample: TelemetrySample, section: str, key: str = "percent") -> float | None:
    value = sample.get(section, {})
    if not isinstance(value, dict):
        return None
    return _round_percent(value.get(key))


class TelemetryHistory:
    def __init__(self, max_samples: int = 60, sampling_interval_seconds: float = 5.0) -> None:
        self.max_samples = max(1, int(max_samples))
        self.sampling_interval_seconds = float(sampling_interval_seconds)
        self.cpu: Deque[float | None] = deque(maxlen=self.max_samples)
        self.ram: Deque[float | None] = deque(maxlen=self.max_samples)
        self.gpu: Deque[float | None] = deque(maxlen=self.max_samples)
        self.samples: Deque[TelemetrySample] = deque(maxlen=self.max_samples)

    def add_sample(self, sample: TelemetrySample) -> TelemetrySample:
        self.samples.append(sample)
        self.cpu.append(telemetry_value(sample, "cpu"))
        self.ram.append(telemetry_value(sample, "ram"))
        self.gpu.append(telemetry_value(sample, "gpu", "usage_percent"))
        return sample

    def collect(self, collector: Callable[[], TelemetrySample] = collect_system_telemetry) -> TelemetrySample:
        return self.add_sample(collector())

    def snapshot(self) -> Dict[str, Any]:
        latest = self.samples[-1] if self.samples else None
        return {
            "status": latest.get("status", "UNKNOWN") if isinstance(latest, dict) else "UNKNOWN",
            "degraded_reason": latest.get("degraded_reason") if isinstance(latest, dict) else None,
            "max_samples": self.max_samples,
            "sampling_interval_seconds": self.sampling_interval_seconds,
            "latest": latest,
            "history": {
                "cpu": list(self.cpu),
                "ram": list(self.ram),
                "gpu": list(self.gpu),
            },
        }


TELEMETRY_HISTORY = TelemetryHistory()


def sample_telemetry(history: TelemetryHistory = TELEMETRY_HISTORY) -> Dict[str, Any]:
    history.collect()
    return history.snapshot()


def sparkline(values: Iterable[float | None], width: int = 24) -> str:
    points = [value for value in values if value is not None]
    if not points:
        return "-" * width
    levels = "▁▂▃▄▅▆▇█"
    visible = points[-width:]
    return "".join(levels[min(len(levels) - 1, max(0, int(round((value / 100) * (len(levels) - 1)))))] for value in visible)


__all__ = [
    "TELEMETRY_HISTORY",
    "TelemetryHistory",
    "collect_gpu_telemetry",
    "collect_system_telemetry",
    "sample_telemetry",
    "sparkline",
    "telemetry_value",
]
