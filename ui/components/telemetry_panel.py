from __future__ import annotations

from typing import Any, Dict

import flet as ft

from core.models import Theme
from core.telemetry import sparkline

TELEMETRY_PANEL_HEIGHT = 192
TELEMETRY_MAX_SUMMARY_LINES = 7

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

TELEMETRY_STYLE_NAMES = {
    "military": "TACTICAL SPIKE GRAPH",
    "eva": "MAGI/LCL SYNC BARS",
    "nerv": "MAGI/LCL SYNC BARS",
    "wh40k": "COGITATOR PURITY BARS",
    "helldivers": "DEMOCRATIC AUTHORIZATION BARS",
    "arasaka": "ASSET UTILIZATION BARS",
    "janus": "DUAL-FRONT MIRROR BARS",
}
TELEMETRY_GRAPH_WIDTH = 30


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
        f"{labels['temp']}: {_temperature(gpu.get('temperature_c'))}",
    ]
    if degraded_reason:
        lines.append(f"Reason: {degraded_reason}")
    return lines


def telemetry_graph_lines(theme_key: str, telemetry: Dict[str, Any] | None) -> list[str]:
    labels = telemetry_labels(theme_key)
    history = telemetry.get("history", {}) if isinstance(telemetry, dict) else {}
    if not isinstance(history, dict):
        history = {}
    cpu_graph = themed_telemetry_graph(theme_key, history.get("cpu", []), TELEMETRY_GRAPH_WIDTH)
    gpu_graph = themed_telemetry_graph(theme_key, history.get("gpu", []), TELEMETRY_GRAPH_WIDTH)
    return [
        f"{TELEMETRY_STYLE_NAMES.get(theme_key, TELEMETRY_STYLE_NAMES['military'])}",
        f"{labels['cpu']} {cpu_graph}",
        f"{labels['gpu']} {gpu_graph}",
    ]


def themed_telemetry_graph(theme_key: str, values: Any, width: int = TELEMETRY_GRAPH_WIDTH) -> str:
    normalized = theme_key.lower()
    if normalized == "military":
        graph = sparkline(values, width=width)
        return graph + (graph[-1:] or "_") * max(0, width - len(graph))
    samples = list(values or [])
    latest = 0.0
    if samples:
        try:
            latest = max(0.0, min(100.0, float(samples[-1])))
        except (TypeError, ValueError):
            latest = 0.0
    filled = int(round((latest / 100.0) * width))
    empty = max(0, width - filled)
    if normalized in {"eva", "nerv"}:
        pattern = ("~^" * ((filled // 2) + 1))[:filled]
        return f"<{pattern}{'.' * empty}>"
    if normalized == "wh40k":
        return f"[{'|' * filled}{'.' * empty}]"
    if normalized == "helldivers":
        return f"[{'=' * filled}{'-' * empty}]"
    if normalized == "arasaka":
        return f"[{'#' * filled}{'.' * empty}]"
    if normalized == "janus":
        left = "|" * (filled // 2)
        right = "|" * (filled - len(left))
        gap = "." * empty
        return f"<{left}{gap}{right}>"
    return sparkline(samples, width=width)


def build_telemetry_panel(theme: Theme, telemetry: Dict[str, Any] | None) -> ft.Control:
    lines = telemetry_summary_lines(theme.key, telemetry)[:TELEMETRY_MAX_SUMMARY_LINES]
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
            spacing=1,
            tight=True,
            scroll=None,
        ),
        height=TELEMETRY_PANEL_HEIGHT,
        width=None,
        expand=False,
        padding=8,
        border=ft.border.all(1, theme.secondary_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


__all__ = [
    "TELEMETRY_MAX_SUMMARY_LINES",
    "TELEMETRY_PANEL_HEIGHT",
    "build_telemetry_panel",
    "TELEMETRY_GRAPH_WIDTH",
    "TELEMETRY_STYLE_NAMES",
    "telemetry_graph_lines",
    "telemetry_labels",
    "telemetry_summary_lines",
    "themed_telemetry_graph",
]
