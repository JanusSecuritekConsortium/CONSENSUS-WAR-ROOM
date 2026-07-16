from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import flet as ft

from core.models import Theme
from core.telemetry import (
    CPU_TEMP_THRESHOLDS,
    GPU_TEMP_THRESHOLDS,
    TEMPERATURE_STALE_SECONDS,
    classify_temperature,
    validate_temperature_c,
    worst_thermal_state,
)


CANONICAL_METRICS = ("cpu", "memory", "disk", "gpu", "vram")
TELEMETRY_HISTORY_LIMIT = 30
TELEMETRY_MIN_UPDATE_SECONDS = 1.0
TELEMETRY_COMPACT_THRESHOLD = 340
EVA_MAGI_METER_HEIGHT = 32

TELEMETRY_LAYOUT_IDS = {
    "janus": "janus_trace_v2",
    "arasaka": "arasaka_activity_bank_v2",
    "eva": "eva_magi_columns_v2",
    "nerv": "eva_magi_columns_v2",
    "wh40k": "wh40k_cogitator_v2",
    "helldivers": "helldivers_readiness_v2",
    "military": "military_matrix_v2",
}

THEME_TELEMETRY_ALIASES: dict[str, dict[str, str]] = {
    "janus": {"cpu": "CPU", "memory": "MEMORY", "disk": "DISK", "gpu": "GPU", "vram": "VRAM"},
    "arasaka": {"cpu": "ASSET LOAD", "memory": "NEURAL", "disk": "DISK", "gpu": "GPU CAPITAL", "vram": "VRAM EQUITY"},
    "eva": {"cpu": "MELCHIOR", "memory": "BALTHASAR", "disk": "DISK", "gpu": "CASPER", "vram": "A.T. FIELD"},
    "nerv": {"cpu": "MELCHIOR", "memory": "BALTHASAR", "disk": "DISK", "gpu": "CASPER", "vram": "A.T. FIELD"},
    "wh40k": {"cpu": "MACHINE SPIRIT", "memory": "DATA-VAULT", "disk": "DISK", "gpu": "GPU RELIQUARY", "vram": "VRAM"},
    "helldivers": {"cpu": "DEMOCRACY", "memory": "LIBERTY ENGINE", "disk": "DISK", "gpu": "ORBITAL SYSTEM", "vram": "ORBITAL VRAM"},
    "military": {"cpu": "CPU", "memory": "MEM", "disk": "DISK", "gpu": "GPU", "vram": "VRAM"},
}

THEME_TELEMETRY_DESIGNS = {
    "janus": "dominant analytical dual trace",
    "arasaka": "vertical corporate activity bank",
    "eva": "vertical MAGI synchronization columns",
    "nerv": "vertical MAGI synchronization columns",
    "wh40k": "cogitator vertical meter assembly",
    "helldivers": "horizontal readiness authorization",
    "military": "tactical load matrix",
}


@dataclass(frozen=True)
class TelemetryMetric:
    key: str
    alias: str
    value: float | None
    available: bool


def _clamp_percent(value: Any) -> float | None:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return None


def _latest_payload(metrics: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(metrics, Mapping):
        return {}
    latest = metrics.get("latest", metrics)
    return latest if isinstance(latest, Mapping) else {}


def _history_payload(metrics: Mapping[str, Any] | None, history: Any = None) -> Mapping[str, Any]:
    if isinstance(history, Mapping):
        return history
    if hasattr(history, "snapshot"):
        snapshot = history.snapshot()
        payload = snapshot.get("history", {}) if isinstance(snapshot, Mapping) else {}
        return payload if isinstance(payload, Mapping) else {}
    if isinstance(metrics, Mapping):
        payload = metrics.get("history", {})
        return payload if isinstance(payload, Mapping) else {}
    return {}


def _section_percent(latest: Mapping[str, Any], section: str, key: str = "percent") -> float | None:
    payload = latest.get(section, {})
    if not isinstance(payload, Mapping):
        return None
    return _clamp_percent(payload.get(key))


def _bounded_history(values: Any) -> list[float]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return []
    bounded = [_clamp_percent(value) for value in list(values)[-TELEMETRY_HISTORY_LIMIT:]]
    return [value for value in bounded if value is not None]


def _last_valid(values: Sequence[Any]) -> float | None:
    bounded = _bounded_history(values)
    return bounded[-1] if bounded else None


def _value_or_history(value: float | None, history_values: Sequence[Any]) -> float | None:
    return value if value is not None else _last_valid(history_values)


def canonical_telemetry_values(metrics: Mapping[str, Any] | None, history: Any = None) -> dict[str, float | None]:
    latest = _latest_payload(metrics)
    history_payload = _history_payload(metrics, history)
    gpu_payload = latest.get("gpu", {}) if isinstance(latest.get("gpu"), Mapping) else {}
    return {
        "cpu": _value_or_history(_section_percent(latest, "cpu"), list(history_payload.get("cpu", []) or [])),
        "memory": _value_or_history(_section_percent(latest, "ram"), list(history_payload.get("ram", []) or [])),
        "disk": _section_percent(latest, "disk"),
        "gpu": _value_or_history(_clamp_percent(gpu_payload.get("usage_percent")), list(history_payload.get("gpu", []) or [])),
        "vram": _clamp_percent(gpu_payload.get("vram_percent")),
    }


def canonical_temperature_values(metrics: Mapping[str, Any] | None, history: Any = None) -> dict[str, Any]:
    latest = _latest_payload(metrics)
    history_payload = _history_payload(metrics, history)
    thermal = latest.get("thermal", {}) if isinstance(latest.get("thermal"), Mapping) else {}
    gpu_payload = latest.get("gpu", {}) if isinstance(latest.get("gpu"), Mapping) else {}
    cpu = validate_temperature_c(latest.get("cpu_package_temp_c") or thermal.get("cpu_package_temp_c"))
    gpu = validate_temperature_c(latest.get("gpu_core_temp_c") or thermal.get("gpu_core_temp_c") or gpu_payload.get("temperature_c"))
    cpu = cpu if cpu is not None else _last_valid(list(history_payload.get("cpu_temp", []) or []))
    gpu = gpu if gpu is not None else _last_valid(list(history_payload.get("gpu_temp", []) or []))
    age = thermal.get("sensor_age_seconds")
    stale = bool(age is not None and float(age) > TEMPERATURE_STALE_SECONDS)
    return {
        "cpu": cpu,
        "gpu": gpu,
        "cpu_source": thermal.get("cpu_temperature_source", "unavailable") if cpu is not None else "unavailable",
        "gpu_source": thermal.get("gpu_temperature_source", gpu_payload.get("temperature_source", "unavailable")) if gpu is not None else "unavailable",
        "gpu_hotspot": validate_temperature_c(thermal.get("gpu_hotspot_temp_c")),
        "vram": validate_temperature_c(thermal.get("vram_temp_c")),
        "storage": validate_temperature_c(thermal.get("storage_temp_c")),
        "sensor_age_seconds": age,
        "stale": stale,
        "thermal_state": "STALE" if stale else worst_thermal_state(cpu, gpu),
    }


def themed_metric_aliases(theme_id: str) -> dict[str, str]:
    return THEME_TELEMETRY_ALIASES.get(theme_id.lower(), THEME_TELEMETRY_ALIASES["military"])


def themed_metrics(theme_id: str, metrics: Mapping[str, Any] | None, history: Any = None) -> list[TelemetryMetric]:
    aliases = themed_metric_aliases(theme_id)
    values = canonical_telemetry_values(metrics, history)
    return [TelemetryMetric(key, aliases[key], values[key], values[key] is not None) for key in CANONICAL_METRICS]


def _percent_text(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}%"


def _temp_text(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.0f} C"


def _theme_colors(theme: Theme) -> dict[str, str]:
    return {
        "active": theme.primary_color,
        "secondary": theme.secondary_color,
        "accent": theme.accent_color,
        "text": theme.panel_value or theme.text_color,
        "muted": theme.secondary_text or theme.muted_text or theme.secondary_color,
        "surface": theme.surface_color,
        "warning": theme.warning_color,
    }


def segmented_bar(value: float | None, segments: int = 12, width: int = 150, height: int = 8, active_color: str | None = None, inactive_color: str | None = None) -> ft.Control:
    bounded = _clamp_percent(value) or 0.0
    active_segments = round((bounded / 100.0) * segments)
    segment_width = max(2, int((width - max(0, segments - 1) * 2) / segments))
    return ft.Row(
        [
            ft.Container(width=segment_width, height=height, bgcolor=active_color if index < active_segments else inactive_color)
            for index in range(segments)
        ],
        spacing=2,
        tight=True,
        data={"role": "segmented_bar", "value": bounded, "segments": segments, "active_segments": active_segments},
    )


def _text(value: str, theme: Theme, color: str, size: int = 10, width: int | None = None, bold: bool = False) -> ft.Text:
    return ft.Text(value, color=color, font_family=theme.font_family, size=size, width=width, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, weight=ft.FontWeight.BOLD if bold else None)


def sparkline(values: Sequence[float], width: int, height: int, color: str, *, role: str = "telemetry_sparkline") -> ft.Control:
    points = _bounded_history(values)
    if len(points) < 2:
        points = points or [0.0]
        points = [points[-1], points[-1]]
    visible = points[-TELEMETRY_HISTORY_LIMIT:]
    bar_width = max(2, int(width / max(1, len(visible))) - 1)
    return ft.Container(
        width=width,
        height=height,
        content=ft.Row(
            [ft.Container(width=bar_width, height=max(2, int((value / 100.0) * height)), bgcolor=color, opacity=0.35 + (0.65 * value / 100.0)) for value in visible],
            spacing=1,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.END,
        ),
        alignment=ft.alignment.bottom_left,
        data={"role": role, "points": len(visible), "width": width, "height": height},
    )


def vertical_meter(
    label: str,
    value: float | None,
    theme: Theme,
    colors: Mapping[str, str],
    *,
    height: int = 44,
    role: str = "vertical_meter",
    threshold: float = 100.0,
    value_formatter=_percent_text,
) -> ft.Control:
    bounded = max(0.0, min(float(threshold), float(value or 0.0)))
    filled = max(2, int((bounded / threshold) * height))
    return ft.Column(
        [
            _text(label, theme, colors["muted"], 9, bold=True),
            _text(value_formatter(value), theme, colors["text"], 10),
            ft.Stack(
                [
                    ft.Container(width=13, height=height, border=ft.border.all(1, colors["muted"]), bgcolor=colors["surface"]),
                    ft.Container(width=13, height=filled, bottom=0, bgcolor=colors["active"]),
                ],
                width=13,
                height=height,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            ),
        ],
        spacing=1,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True,
        data={"role": role, "label": label, "value": value, "threshold": threshold, "height": height},
    )


def _metric_map(theme_id: str, metrics: Mapping[str, Any] | None, history: Any) -> dict[str, TelemetryMetric]:
    return {metric.key: metric for metric in themed_metrics(theme_id, metrics, history)}


def _history(history_payload: Mapping[str, Any], key: str) -> list[float]:
    return _bounded_history(history_payload.get("ram" if key == "memory" else key, []))


def _thermal_line(theme: Theme, colors: Mapping[str, str], temps: Mapping[str, Any], cpu_label: str = "CPU TEMP", gpu_label: str = "GPU TEMP") -> ft.Control:
    return ft.Row(
        [
            _text(f"{cpu_label} {_temp_text(temps['cpu'])}", theme, colors["text"], 10),
            _text(f"{gpu_label} {_temp_text(temps['gpu'])}", theme, colors["text"], 10),
            _text(f"THERMAL {temps['thermal_state']}", theme, colors["warning"] if temps["thermal_state"] in {"HOT", "CRITICAL", "STALE"} else colors["muted"], 10),
        ],
        spacing=10,
        tight=True,
        data={"role": "thermal_readout", "cpu": temps["cpu"], "gpu": temps["gpu"], "thermal_state": temps["thermal_state"]},
    )


def _secondary_pair(metric_map: Mapping[str, TelemetryMetric], theme: Theme, colors: Mapping[str, str]) -> ft.Control:
    disk = metric_map["disk"]
    vram = metric_map["vram"]
    return ft.Row(
        [
            _text(f"{disk.alias} {_percent_text(disk.value)}", theme, colors["text"], 10),
            _text(f"{vram.alias} {_percent_text(vram.value)}", theme, colors["text"], 10),
        ],
        spacing=20,
        tight=True,
        data={"role": "telemetry_secondary_values"},
    )


def _wrap(theme_key: str, theme: Theme, rows: list[ft.Control], metric_map: Mapping[str, TelemetryMetric], temps: Mapping[str, Any], *, compact: bool, layout_id: str) -> ft.Column:
    return ft.Column(
        rows,
        spacing=1 if compact else 2,
        tight=True,
        scroll=None,
        data={
            "role": "header_telemetry_panel_content",
            "theme": theme_key,
            "telemetry_layout_id": layout_id,
            "design": THEME_TELEMETRY_DESIGNS.get(theme_key, THEME_TELEMETRY_DESIGNS["military"]),
            "canonical_metrics": CANONICAL_METRICS,
            "aliases": {key: metric.alias for key, metric in metric_map.items()},
            "values": {key: metric.value for key, metric in metric_map.items()},
            "temperatures": dict(temps),
            "compact": compact,
            "compact_threshold": TELEMETRY_COMPACT_THRESHOLD,
            "history_limit": TELEMETRY_HISTORY_LIMIT,
            "min_update_seconds": TELEMETRY_MIN_UPDATE_SECONDS,
        },
    )


def estimate_eva_telemetry_content_height(*, compact: bool = False) -> int:
    row_spacing = 1 if compact else 2
    title_height = 13
    magi_meter_height = 9 + 10 + EVA_MAGI_METER_HEIGHT + 2
    thermal_row_height = 10
    secondary_row_height = 10
    return title_height + magi_meter_height + thermal_row_height + secondary_row_height + (row_spacing * 3)


def build_janus_telemetry(theme_id: str, metrics: Mapping[str, Any] | None, history: Any, palette: Theme, *, available_width: int = 360) -> ft.Control:
    colors = _theme_colors(palette)
    metric = _metric_map(theme_id, metrics, history)
    temps = canonical_temperature_values(metrics, history)
    hist = _history_payload(metrics, history)
    compact = available_width < TELEMETRY_COMPACT_THRESHOLD
    trace_width = 205 if not compact else 150
    rows = [
        _text("LIVE TELEMETRY", palette, colors["accent"], 13, bold=True),
        ft.Row([_text(f"CPU {_percent_text(metric['cpu'].value)}", palette, colors["text"], 10), _text(f"MEMORY {_percent_text(metric['memory'].value)}", palette, colors["text"], 10), _text(f"GPU {_percent_text(metric['gpu'].value)}", palette, colors["text"], 10)], spacing=12, tight=True),
        ft.Row([sparkline(_history(hist, "cpu"), trace_width, 25, colors["accent"], role="dominant_sparkline"), sparkline(_history(hist, "gpu"), trace_width, 25, colors["muted"], role="dominant_sparkline")], spacing=4, tight=True, data={"role": "janus_dual_trace", "dominant_width": trace_width}),
        _thermal_line(palette, colors, temps, "THERMAL CPU", "GPU"),
        _secondary_pair(metric, palette, colors),
    ]
    return _wrap(theme_id, palette, rows, metric, temps, compact=compact, layout_id="janus_trace_v2")


def build_arasaka_telemetry(theme_id: str, metrics: Mapping[str, Any] | None, history: Any, palette: Theme, *, available_width: int = 360) -> ft.Control:
    colors = _theme_colors(palette)
    metric = _metric_map(theme_id, metrics, history)
    temps = canonical_temperature_values(metrics, history)
    hist = _history_payload(metrics, history)
    compact = available_width < TELEMETRY_COMPACT_THRESHOLD
    samples = (_history(hist, "cpu") + _history(hist, "memory") + _history(hist, "gpu"))[-12:]
    samples = (samples or [metric["cpu"].value or 0.0, metric["memory"].value or 0.0, metric["gpu"].value or 0.0])[-12:]
    samples = ([0.0] * max(0, 12 - len(samples))) + samples
    bank = ft.Row(
        [ft.Container(width=7, height=max(3, int(34 * value / 100.0)), bgcolor=colors["active"]) for value in samples],
        spacing=4,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.END,
        data={"role": "vertical_activity_bank", "columns": 12},
    )
    thermal = ft.Row(
        [
            vertical_meter("CORE TEMP", temps["cpu"], palette, colors, height=34, role="thermal_vertical_meter", threshold=CPU_TEMP_THRESHOLDS["critical"], value_formatter=_temp_text),
            vertical_meter("GPU TEMP", temps["gpu"], palette, colors, height=34, role="thermal_vertical_meter", threshold=GPU_TEMP_THRESHOLDS["critical"], value_formatter=_temp_text),
        ],
        spacing=12,
        tight=True,
    )
    rows = [
        _text("LIVE TELEMETRY", palette, colors["accent"], 13, bold=True),
        ft.Row([_text(f"ASSET LOAD {_percent_text(metric['cpu'].value)}", palette, colors["text"], 10), _text(f"NEURAL {_percent_text(metric['memory'].value)}", palette, colors["text"], 10)], spacing=14, tight=True),
        ft.Row([bank, thermal], spacing=12, tight=True, data={"role": "arasaka_activity_with_thermal"}),
        _text(f"GPU CAPITAL {_percent_text(metric['gpu'].value)}", palette, colors["text"], 10),
        _secondary_pair(metric, palette, colors),
    ]
    return _wrap(theme_id, palette, rows, metric, temps, compact=compact, layout_id="arasaka_activity_bank_v2")


def build_eva_telemetry(theme_id: str, metrics: Mapping[str, Any] | None, history: Any, palette: Theme, *, available_width: int = 360) -> ft.Control:
    colors = _theme_colors(palette)
    metric = _metric_map(theme_id, metrics, history)
    temps = canonical_temperature_values(metrics, history)
    compact = available_width < TELEMETRY_COMPACT_THRESHOLD
    meters = ft.Row(
        [vertical_meter(metric[key].alias, metric[key].value, palette, colors, height=EVA_MAGI_METER_HEIGHT, role="magi_vertical_channel") for key in ("cpu", "memory", "gpu")],
        spacing=20 if not compact else 10,
        tight=True,
        data={"role": "magi_channel_row", "vertical_meter_count": 3},
    )
    thermal = ft.Row(
        [
            _text(f"CORE {_temp_text(temps['cpu'])}", palette, colors["text"], 10),
            _text(f"PATTERN {_temp_text(temps['gpu'])}", palette, colors["text"], 10),
            _text(f"THERMAL {temps['thermal_state']}", palette, colors["warning"] if temps["thermal_state"] in {"HOT", "CRITICAL", "STALE"} else colors["muted"], 10),
        ],
        spacing=14 if not compact else 8,
        tight=True,
        data={"role": "at_thermal_compact_row"},
    )
    rows = [_text("LIVE TELEMETRY", palette, colors["accent"], 13, bold=True), meters, thermal, _secondary_pair(metric, palette, colors)]
    control = _wrap(theme_id, palette, rows, metric, temps, compact=compact, layout_id="eva_magi_columns_v2")
    control.data["estimated_content_height"] = estimate_eva_telemetry_content_height(compact=compact)
    control.data["magi_meter_height"] = EVA_MAGI_METER_HEIGHT
    return control


def build_wh40k_telemetry(theme_id: str, metrics: Mapping[str, Any] | None, history: Any, palette: Theme, *, available_width: int = 360) -> ft.Control:
    colors = _theme_colors(palette)
    metric = _metric_map(theme_id, metrics, history)
    temps = canonical_temperature_values(metrics, history)
    compact = available_width < TELEMETRY_COMPACT_THRESHOLD
    reliquaries = ft.Row(
        [
            vertical_meter("MACHINE SPIRIT", metric["cpu"].value, palette, colors, height=42, role="mechanical_vertical_meter"),
            vertical_meter("DATA-VAULT", metric["memory"].value, palette, colors, height=42, role="mechanical_vertical_meter"),
            vertical_meter("REACTOR CORE", temps["cpu"], palette, colors, height=34, role="thermal_vertical_meter", threshold=CPU_TEMP_THRESHOLDS["critical"], value_formatter=_temp_text),
            vertical_meter("RELIQUARY CORE", temps["gpu"], palette, colors, height=34, role="thermal_vertical_meter", threshold=GPU_TEMP_THRESHOLDS["critical"], value_formatter=_temp_text),
        ],
        spacing=13 if not compact else 8,
        tight=True,
        data={"role": "wh40k_reliquary_meters"},
    )
    chain = ft.Row(
        [_text("GPU RELIQUARY", palette, colors["muted"], 10), segmented_bar(metric["gpu"].value, 14, 130, 7, colors["active"], colors["surface"]), _text(_percent_text(metric["gpu"].value), palette, colors["text"], 10)],
        spacing=7,
        tight=True,
        data={"role": "horizontal_chain_meter", "count": 1},
    )
    rows = [_text("LIVE TELEMETRY", palette, colors["accent"], 14, bold=True), reliquaries, chain, _secondary_pair(metric, palette, colors)]
    return _wrap(theme_id, palette, rows, metric, temps, compact=compact, layout_id="wh40k_cogitator_v2")


def build_helldivers_telemetry(theme_id: str, metrics: Mapping[str, Any] | None, history: Any, palette: Theme, *, available_width: int = 360) -> ft.Control:
    colors = _theme_colors(palette)
    metric = _metric_map(theme_id, metrics, history)
    temps = canonical_temperature_values(metrics, history)
    compact = available_width < TELEMETRY_COMPACT_THRESHOLD

    def readiness(key: str) -> ft.Control:
        item = metric[key]
        return ft.Row([_text(item.alias, palette, colors["muted"], 10, 96), segmented_bar(item.value, 10, 108, 8, colors["active"], colors["secondary"]), _text(_percent_text(item.value), palette, colors["text"], 10)], spacing=5, tight=True, data={"role": "horizontal_readiness_bar"})

    auth = ft.Row(
        [ft.Container(width=12, height=8, bgcolor=colors["active"] if index % 2 == 0 else colors["secondary"]) for index in range(14)],
        spacing=2,
        tight=True,
        data={"role": "authorization_strip", "segments": 14},
    )
    rows = [
        _text("LIVE TELEMETRY", palette, colors["accent"], 13, bold=True),
        readiness("cpu"),
        readiness("memory"),
        readiness("gpu"),
        ft.Row([_text("AUTHORIZATION", palette, colors["muted"], 10), auth], spacing=8, tight=True),
        _thermal_line(palette, colors, temps, "REACTOR TEMP", "ORBITAL GPU"),
        _secondary_pair(metric, palette, colors),
    ]
    return _wrap(theme_id, palette, rows, metric, temps, compact=compact, layout_id="helldivers_readiness_v2")


def build_military_telemetry(theme_id: str, metrics: Mapping[str, Any] | None, history: Any, palette: Theme, *, available_width: int = 360) -> ft.Control:
    colors = _theme_colors(palette)
    metric = _metric_map(theme_id, metrics, history)
    temps = canonical_temperature_values(metrics, history)
    compact = available_width < TELEMETRY_COMPACT_THRESHOLD
    matrix_rows = []
    for key in ("cpu", "memory", "gpu"):
        active = round(((metric[key].value or 0.0) / 100.0) * 12)
        matrix_rows.append(
            ft.Row(
                [ft.Container(width=8, height=8, bgcolor=colors["active"] if index < active else colors["surface"], border=ft.border.all(1, colors["muted"])) for index in range(12)],
                spacing=3,
                tight=True,
            )
        )
    matrix = ft.Column(matrix_rows, spacing=3, tight=True, data={"role": "tactical_load_matrix", "rows": 3, "columns": 12})
    rows = [
        _text("LIVE TELEMETRY", palette, colors["accent"], 13, bold=True),
        ft.Row([_text(f"CPU {_percent_text(metric['cpu'].value)}", palette, colors["text"], 10), _text(f"MEM {_percent_text(metric['memory'].value)}", palette, colors["text"], 10), _text(f"GPU {_percent_text(metric['gpu'].value)}", palette, colors["text"], 10)], spacing=12, tight=True),
        _text("TACTICAL LOAD MATRIX", palette, colors["accent"], 10, bold=True),
        matrix,
        _thermal_line(palette, colors, temps, "CPU TEMP", "GPU TEMP"),
        _secondary_pair(metric, palette, colors),
    ]
    return _wrap(theme_id, palette, rows, metric, temps, compact=compact, layout_id="military_matrix_v2")


def build_themed_telemetry(theme_id: str, metrics: Mapping[str, Any] | None, history: Any, palette: Theme, *, available_width: int = 360) -> ft.Control:
    theme_key = theme_id.lower()
    builders = {
        "janus": build_janus_telemetry,
        "arasaka": build_arasaka_telemetry,
        "eva": build_eva_telemetry,
        "nerv": build_eva_telemetry,
        "wh40k": build_wh40k_telemetry,
        "helldivers": build_helldivers_telemetry,
        "military": build_military_telemetry,
    }
    return builders.get(theme_key, build_military_telemetry)(theme_key, metrics, history, palette, available_width=available_width)


def telemetry_control_signature(control: ft.Control) -> tuple:
    roles: list[str] = []

    def walk(node: Any) -> None:
        data = getattr(node, "data", None)
        if isinstance(data, Mapping) and data.get("role"):
            roles.append(str(data["role"]))
        content = getattr(node, "content", None)
        if content is not None:
            walk(content)
        for child in getattr(node, "controls", []) or []:
            walk(child)

    walk(control)
    top_type = type(control).__name__
    orientation = "column" if isinstance(control, ft.Column) else ("row" if isinstance(control, ft.Row) else top_type.lower())
    return (
        top_type,
        orientation,
        roles.count("horizontal_readiness_bar"),
        roles.count("mechanical_vertical_meter") + roles.count("magi_vertical_channel") + roles.count("thermal_vertical_meter"),
        "tactical_load_matrix" in roles,
        "dominant_sparkline" in roles,
        len(getattr(control, "controls", []) or []),
        getattr(control, "data", {}).get("telemetry_layout_id") if isinstance(getattr(control, "data", None), Mapping) else None,
    )


def bounded_history_deque() -> deque[float | None]:
    return deque(maxlen=TELEMETRY_HISTORY_LIMIT)


__all__ = [
    "CANONICAL_METRICS",
    "EVA_MAGI_METER_HEIGHT",
    "TELEMETRY_COMPACT_THRESHOLD",
    "TELEMETRY_HISTORY_LIMIT",
    "TELEMETRY_LAYOUT_IDS",
    "TELEMETRY_MIN_UPDATE_SECONDS",
    "THEME_TELEMETRY_ALIASES",
    "THEME_TELEMETRY_DESIGNS",
    "TelemetryMetric",
    "bounded_history_deque",
    "build_arasaka_telemetry",
    "build_eva_telemetry",
    "build_helldivers_telemetry",
    "build_janus_telemetry",
    "build_military_telemetry",
    "build_themed_telemetry",
    "build_wh40k_telemetry",
    "canonical_telemetry_values",
    "canonical_temperature_values",
    "estimate_eva_telemetry_content_height",
    "segmented_bar",
    "sparkline",
    "telemetry_control_signature",
    "themed_metric_aliases",
    "themed_metrics",
    "vertical_meter",
]
