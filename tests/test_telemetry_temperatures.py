from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import core.telemetry as telemetry
from core.telemetry import (
    TelemetryHistory,
    validate_temperature_c,
    worst_thermal_state,
)
from ui.components.telemetry_widgets import (
    build_themed_telemetry,
    canonical_temperature_values,
)
from ui.themes.catalog import GUI_THEME_KEYS, THEMES


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def _text(control) -> str:
    return "\n".join(str(child.value) for child in _walk(control) if hasattr(child, "value"))


def _sample(cpu_temp=None, gpu_temp=None, age=0.0):
    return {
        "cpu_percent": 32.0,
        "memory_percent": 64.0,
        "disk_percent": 78.0,
        "gpu_percent": 24.0,
        "vram_percent": 31.0,
        "cpu_package_temp_c": cpu_temp,
        "gpu_core_temp_c": gpu_temp,
        "thermal": {
            "cpu_package_temp_c": cpu_temp,
            "gpu_core_temp_c": gpu_temp,
            "sensor_age_seconds": age,
        },
    }


def test_temperature_validation_rejects_invalid_sensor_values() -> None:
    assert validate_temperature_c(54.312) == 54.31
    assert validate_temperature_c(-20.0) == -20.0
    assert validate_temperature_c(130.0) == 130.0
    assert validate_temperature_c(0.0) is None
    assert validate_temperature_c(float("nan")) is None
    assert validate_temperature_c(float("inf")) is None
    assert validate_temperature_c(-21.0) is None
    assert validate_temperature_c(131.0) is None
    assert validate_temperature_c(None) is None


def test_thermal_state_uses_worst_available_primary_temperature() -> None:
    assert worst_thermal_state(54.0, 47.0) == "NORMAL"
    assert worst_thermal_state(72.0, 47.0) == "ELEVATED"
    assert worst_thermal_state(86.0, 47.0) == "HOT"
    assert worst_thermal_state(54.0, 89.0) == "CRITICAL"
    assert worst_thermal_state(None, None) == "UNKNOWN"


def test_stale_and_unavailable_temperatures_are_rendered_without_synthetic_values() -> None:
    stale = canonical_temperature_values(_sample(54.0, 47.0, age=11.0))
    unavailable = canonical_temperature_values(_sample(None, None))

    assert stale["thermal_state"] == "STALE"
    assert stale["cpu"] == 54.0
    assert stale["gpu"] == 47.0
    assert unavailable["cpu"] is None
    assert unavailable["gpu"] is None


def test_temperature_histories_are_bounded_to_30_samples() -> None:
    history = TelemetryHistory()

    for index in range(45):
        history.add_sample(_sample(40.0 + index, 50.0 + index))

    snapshot = history.snapshot()
    assert len(snapshot["history"]["cpu_temp"]) == 30
    assert len(snapshot["history"]["gpu_temp"]) == 30
    assert snapshot["history"]["cpu_temp"][-1] == 84.0
    assert snapshot["history"]["gpu_temp"][-1] == 94.0


def test_all_themes_show_cpu_and_gpu_temperatures_or_na() -> None:
    for theme_key in GUI_THEME_KEYS:
        control = build_themed_telemetry(
            theme_key,
            _sample(54.0, 47.0),
            {"cpu": [20.0, 40.0], "gpu": [10.0, 24.0], "memory": [50.0, 64.0]},
            THEMES[theme_key],
        )
        text = _text(control)

        assert "54 C" in text
        assert "47 C" in text


def test_nvidia_smi_temperature_polling_is_cached_within_update_interval() -> None:
    calls = []
    old_path = telemetry._NVIDIA_SMI_PATH
    old_cache = telemetry._NVIDIA_SMI_CACHE
    old_run = telemetry.subprocess.run

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="24,512,1024,55\n", stderr="")

    try:
        telemetry._NVIDIA_SMI_PATH = "nvidia-smi"
        telemetry._NVIDIA_SMI_CACHE = None
        telemetry.subprocess.run = fake_run

        first = telemetry._gpu_from_nvidia_smi()
        second = telemetry._gpu_from_nvidia_smi()

        assert first["temperature_c"] == 55.0
        assert second["temperature_c"] == 55.0
        assert first["temperature_source"] == "nvidia-smi"
        assert len(calls) == 1
    finally:
        telemetry._NVIDIA_SMI_PATH = old_path
        telemetry._NVIDIA_SMI_CACHE = old_cache
        telemetry.subprocess.run = old_run


def test_invalid_temperature_validation_handles_non_finite_math_values() -> None:
    assert validate_temperature_c(math.nan) is None
    assert validate_temperature_c(math.inf) is None
    assert validate_temperature_c(-math.inf) is None


if __name__ == "__main__":
    test_temperature_validation_rejects_invalid_sensor_values()
    test_thermal_state_uses_worst_available_primary_temperature()
    test_stale_and_unavailable_temperatures_are_rendered_without_synthetic_values()
    test_temperature_histories_are_bounded_to_30_samples()
    test_all_themes_show_cpu_and_gpu_temperatures_or_na()
    test_nvidia_smi_temperature_polling_is_cached_within_update_interval()
    test_invalid_temperature_validation_handles_non_finite_math_values()
    print("test_telemetry_temperatures PASS")
