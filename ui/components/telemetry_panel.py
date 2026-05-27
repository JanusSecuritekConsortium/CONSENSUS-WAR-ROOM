from __future__ import annotations

from typing import Any, Dict

import flet as ft

from core.models import Theme
from core.telemetry import sparkline


TELEMETRY_LABELS = {
    "military": {
        "cpu": "CPU LOAD",
        "ram": "MEMORY",
        "gpu": "GPU LOAD",
        "vram": "VRAM",
        "temp": "GPU TEMP",
    },
    "eva": {
        "cpu": "CORE SYNC",
        "ram": "LCL BUFFER",
        "gpu": "ANGEL PATTERN GPU",
        "vram": "A.T. VRAM",
        "temp": "THERMAL",
    },
    "nerv": {
        "cpu": "CORE SYNC",
        "ram": "LCL BUFFER",
        "gpu": "ANGEL PATTERN GPU",
        "vram": "A.T. VRAM",
        "temp": "THERMAL",
    },
    "wh40k": {
        "cpu": "MACHINE SPIRIT LOAD",
        "ram": "DATA-VAULT",
        "gpu": "GPU RELIQUARY",
        "vram": "RELIQUARY VRAM",
        "temp": "HEAT LITANY",
    },
    "helldivers": {
        "cpu": "DEMOCRACY LOAD",
        "ram": "LIBERTY ENGINE",
        "gpu": "ORBITAL GPU",
        "vram": "ORBITAL VRAM",
        "temp": "HELLPOD TEMP",
    },
    "arasaka": {
        "cpu": "ASSET LOAD",
        "ram": "NEURAL UTILIZATION",
        "gpu": "GPU CAPITAL",
        "vram": "VRAM EQUITY",
        "temp": "THERMAL RISK",
    },
    "janus": {
        "cpu": "FRONT-A CPU",
        "ram": "MEMORY GATE",
        "gpu": "FRONT-B GPU",
        "vram": "MIRROR VRAM",
        "temp": "DUAL HEAT",
    },
}


def telemetry_labels(theme_key: str) -> Dict[str, str]:
    return TELEMETRY_LABELS.get(theme_key, TELEMETRY_LABELS["military"])


def _percent(value: Any) -> str:
    if value is None:
        return "UNAVAILABLE"
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "UNAVAILABLE"


def _temperature(value: Any) -> str:
    if value is None:
        return "--"
    try:
        return f"{float(value):.0f}C"
    except (TypeError, ValueError):
        return "--"


def telemetry_summary_lines(theme_key: str, telemetry: Dict[str, Any] | None) -> list[str]:
    labels = telemetry_labels(theme_key)
    latest = telemetry.get("latest", telemetry) if isinstance(telemetry, dict) else {}
    if not isinstance(latest, dict):
        latest = {}
    gpu = latest.get("gpu", {}) if isinstance(latest.get("gpu"), dict) else {}
    degraded_reason = telemetry.get("degraded_reason") if isinstance(telemetry, dict) else None
    degraded_reason = degraded_reason or latest.get("degraded_reason")
    lines = [
        f"{labels['cpu']}: {_percent((latest.get('cpu') or {}).get('percent') if isinstance(latest.get('cpu'), dict) else None)}",
        f"{labels['ram']}: {_percent((latest.get('ram') or {}).get('percent') if isinstance(latest.get('ram'), dict) else None)}",
        f"DISK: {_percent((latest.get('disk') or {}).get('percent') if isinstance(latest.get('disk'), dict) else None)}",
        f"{labels['gpu']}: {_percent(gpu.get('usage_percent'))}",
        f"{labels['vram']}: {_percent(gpu.get('vram_percent'))}",
    ]
    if degraded_reason:
        lines.append(f"Reason: {degraded_reason}")
    if gpu.get("temperature_c") is not None:
        lines.append(f"{labels['temp']}: {_temperature(gpu.get('temperature_c'))}")
    elif gpu.get("status") == "unavailable":
        lines.append(f"{labels['gpu']}: UNAVAILABLE")
    return lines


def telemetry_graph_lines(theme_key: str, telemetry: Dict[str, Any] | None) -> list[str]:
    labels = telemetry_labels(theme_key)
    history = telemetry.get("history", {}) if isinstance(telemetry, dict) else {}
    if not isinstance(history, dict):
        history = {}
    return [
        f"{labels['cpu']} {sparkline(history.get('cpu', []), width=18)}",
        f"{labels['gpu']} {sparkline(history.get('gpu', []), width=18)}",
    ]


def build_telemetry_panel(theme: Theme, telemetry: Dict[str, Any] | None) -> ft.Control:
    lines = telemetry_summary_lines(theme.key, telemetry)
    graph = telemetry_graph_lines(theme.key, telemetry)
    return ft.Container(
        content=ft.Column(
            [
                ft.Text("TELEMETRY", color=theme.accent_color, size=11, weight=ft.FontWeight.BOLD),
                *[
                    ft.Text(line, color=theme.panel_value or theme.text_color, size=10, font_family=theme.font_family)
                    for line in lines
                ],
                *[
                    ft.Text(line, color=theme.secondary_text or theme.secondary_color, size=9, font_family=theme.font_family)
                    for line in graph
                ],
            ],
            spacing=2,
            tight=True,
        ),
        padding=8,
        border=ft.border.all(1, theme.secondary_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


__all__ = ["build_telemetry_panel", "telemetry_graph_lines", "telemetry_labels", "telemetry_summary_lines"]
