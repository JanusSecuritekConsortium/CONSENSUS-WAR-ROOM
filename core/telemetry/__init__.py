from __future__ import annotations

import csv
import math
import shutil
import subprocess
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Callable, Deque, Dict, Iterable

from core.paths import SYSTEM_ROOT


TelemetrySample = Dict[str, Any]
CPU_TEMP_THRESHOLDS = {"normal": 70.0, "warm": 85.0, "critical": 95.0}
GPU_TEMP_THRESHOLDS = {"normal": 65.0, "warm": 80.0, "critical": 88.0}
TEMPERATURE_STALE_SECONDS = 10.0
NVIDIA_SMI_MIN_POLL_SECONDS = 2.0
_NVIDIA_SMI_PATH: str | None = None
_NVIDIA_SMI_CACHE: tuple[float, Dict[str, Any]] | None = None


def _round_percent(value: Any) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def validate_temperature_c(value: Any) -> float | None:
    try:
        temperature = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(temperature) or math.isinf(temperature):
        return None
    if temperature == 0.0:
        return None
    if not -20.0 <= temperature <= 130.0:
        return None
    return round(temperature, 2)


def classify_temperature(value: float | None, thresholds: Dict[str, float]) -> str:
    if value is None:
        return "UNKNOWN"
    if value < thresholds["normal"]:
        return "NORMAL"
    if value < thresholds["warm"]:
        return "ELEVATED"
    if value < thresholds["critical"]:
        return "HOT"
    return "CRITICAL"


def worst_thermal_state(cpu_temp: float | None, gpu_temp: float | None) -> str:
    rank = {"UNKNOWN": 0, "NORMAL": 1, "ELEVATED": 2, "HOT": 3, "CRITICAL": 4}
    states = [
        classify_temperature(cpu_temp, CPU_TEMP_THRESHOLDS),
        classify_temperature(gpu_temp, GPU_TEMP_THRESHOLDS),
    ]
    return max(states, key=lambda state: rank[state])


def _find_nvidia_smi() -> str | None:
    global _NVIDIA_SMI_PATH
    if _NVIDIA_SMI_PATH is None:
        _NVIDIA_SMI_PATH = shutil.which("nvidia-smi") or ""
    return _NVIDIA_SMI_PATH or None


def _unavailable_gpu(source: str = "unavailable", reason: str = "gpu_backend_unavailable") -> Dict[str, Any]:
    return {
        "status": "unavailable",
        "source": source,
        "usage_percent": None,
        "vram_percent": None,
        "temperature_c": None,
        "temperature_source": "unavailable",
        "reason": reason,
    }


def _gpu_from_nvidia_smi() -> Dict[str, Any]:
    global _NVIDIA_SMI_CACHE
    nvidia_smi = _find_nvidia_smi()
    if nvidia_smi is None:
        raise RuntimeError("nvidia-smi not found")
    now = monotonic()
    if _NVIDIA_SMI_CACHE is not None and now - _NVIDIA_SMI_CACHE[0] < NVIDIA_SMI_MIN_POLL_SECONDS:
        return dict(_NVIDIA_SMI_CACHE[1])
    completed = subprocess.run(
        [
            nvidia_smi,
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
    temp = validate_temperature_c(row[3])
    vram = round((used / total) * 100, 2) if used is not None and total else None
    payload = {
        "status": "ready",
        "source": "nvidia-smi",
        "usage_percent": usage,
        "vram_percent": vram,
        "temperature_c": temp,
        "temperature_source": "nvidia-smi" if temp is not None else "unavailable",
    }
    _NVIDIA_SMI_CACHE = (now, dict(payload))
    return payload


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
        "temperature_c": validate_temperature_c(getattr(gpu, "temperature", None)),
        "temperature_source": "GPUtil",
    }


def collect_gpu_telemetry() -> Dict[str, Any]:
    try:
        return _gpu_from_nvidia_smi()
    except Exception as nvidia_error:
        try:
            return _gpu_from_gputil()
        except Exception as gputil_error:
            return _unavailable_gpu(reason=f"{nvidia_error}; {gputil_error}")


def collect_cpu_package_temperature() -> Dict[str, Any]:
    try:
        import psutil  # type: ignore

        sensors = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
        for name, readings in sensors.items():
            normalized_name = str(name).lower()
            if "acpi" in normalized_name:
                continue
            for reading in readings:
                label = str(getattr(reading, "label", "")).lower()
                if not any(token in f"{normalized_name} {label}" for token in ("package", "cpu", "coretemp", "k10temp")):
                    continue
                value = validate_temperature_c(getattr(reading, "current", None))
                if value is not None:
                    return {"value": value, "source": f"psutil:{name}", "sensor_age_seconds": 0.0}
    except Exception:
        pass
    return {"value": None, "source": "unavailable", "sensor_age_seconds": None}


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
    cpu_temp = collect_cpu_package_temperature()
    gpu_temp = validate_temperature_c(gpu.get("temperature_c"))
    sample["gpu"] = gpu
    sample["source"]["gpu"] = gpu.get("source", "unavailable")
    sample["thermal"] = {
        "cpu_package_temp_c": cpu_temp["value"],
        "cpu_temperature_source": cpu_temp["source"],
        "gpu_core_temp_c": gpu_temp,
        "gpu_temperature_source": gpu.get("temperature_source", "unavailable") if gpu_temp is not None else "unavailable",
        "gpu_hotspot_temp_c": None,
        "vram_temp_c": None,
        "storage_temp_c": None,
        "sensor_age_seconds": cpu_temp["sensor_age_seconds"],
        "thermal_state": worst_thermal_state(cpu_temp["value"], gpu_temp),
    }
    sample["cpu_package_temp_c"] = cpu_temp["value"]
    sample["gpu_core_temp_c"] = gpu_temp
    sample["gpu_hotspot_temp_c"] = None
    sample["vram_temp_c"] = None
    sample["storage_temp_c"] = None
    return sample


def telemetry_value(sample: TelemetrySample, section: str, key: str = "percent") -> float | None:
    value = sample.get(section, {})
    if not isinstance(value, dict):
        return None
    return _round_percent(value.get(key))


class TelemetryHistory:
    def __init__(self, max_samples: int = 30, sampling_interval_seconds: float = 1.0) -> None:
        self.max_samples = max(1, int(max_samples))
        self.sampling_interval_seconds = max(1.0, float(sampling_interval_seconds))
        self.cpu: Deque[float | None] = deque(maxlen=self.max_samples)
        self.ram: Deque[float | None] = deque(maxlen=self.max_samples)
        self.gpu: Deque[float | None] = deque(maxlen=self.max_samples)
        self.cpu_temp: Deque[float | None] = deque(maxlen=self.max_samples)
        self.gpu_temp: Deque[float | None] = deque(maxlen=self.max_samples)
        self.samples: Deque[TelemetrySample] = deque(maxlen=self.max_samples)

    def add_sample(self, sample: TelemetrySample) -> TelemetrySample:
        self.samples.append(sample)
        self.cpu.append(telemetry_value(sample, "cpu"))
        self.ram.append(telemetry_value(sample, "ram"))
        self.gpu.append(telemetry_value(sample, "gpu", "usage_percent"))
        self.cpu_temp.append(validate_temperature_c(sample.get("cpu_package_temp_c")))
        self.gpu_temp.append(validate_temperature_c(sample.get("gpu_core_temp_c")))
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
                "cpu_temp": list(self.cpu_temp),
                "gpu_temp": list(self.gpu_temp),
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
    "CPU_TEMP_THRESHOLDS",
    "GPU_TEMP_THRESHOLDS",
    "NVIDIA_SMI_MIN_POLL_SECONDS",
    "TEMPERATURE_STALE_SECONDS",
    "classify_temperature",
    "collect_gpu_telemetry",
    "collect_cpu_package_temperature",
    "collect_system_telemetry",
    "sample_telemetry",
    "sparkline",
    "telemetry_value",
    "validate_temperature_c",
    "worst_thermal_state",
]
