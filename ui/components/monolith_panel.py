from __future__ import annotations

import re
from typing import Dict

import flet as ft

from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from core.models import NodeIdentity, Theme


READINESS_ROW_LABELS = ("SESSION", "MEMORY", "THEME", "PROVIDER", "LAST VERDICT", "LIFECYCLE")
READINESS_LABEL_WIDTH = 78
READINESS_ROW_FONT_SIZE = 9
MONOLITH_CARD_COUNT = 4
MONOLITH_CARD_PADDING = 8


def status_color_category(status: str) -> str:
    normalized = status.upper()
    if normalized in {"ONLINE", "IDLE", "APPROVE", "APPROVED", "SUCCESS", "OK"}:
        return "success"
    if normalized in {"THINKING", "ANALYZING", "VOTING", "SYNCHRONIZING"}:
        return "thinking"
    if normalized in {"DEGRADED", "CONDITIONAL", "ABSTAIN", "NO_CONSENSUS", "CAUTION", "ESCALATE", "HUMAN_REVIEW_REQUIRED", "DEADLOCK"}:
        return "warning"
    if normalized in {"OFFLINE", "ERROR", "DENY", "DENIED"}:
        return "error"
    return "warning"


def status_color(theme: Theme, status: str) -> str:
    category = status_color_category(status)
    if category == "success":
        return theme.primary_color
    if category == "thinking":
        return theme.accent_color
    if category == "error":
        return theme.error_color
    return theme.warning_color


def _status_glyph(status: str) -> str:
    category = status_color_category(status)
    if category == "success":
        return "*"
    if category == "thinking":
        return ">"
    if category == "error":
        return "!"
    return "+"


def _runtime_color(theme: Theme, state: str) -> str:
    normalized = state.upper()
    if normalized in {"ERROR", "OFFLINE"}:
        return theme.error_color
    if normalized in {"THINKING", "ANALYZING", "VOTING", "SYNCHRONIZING"}:
        return theme.accent_color
    return theme.secondary_text or theme.secondary_color


def _compact_model_name(model: str) -> str:
    candidate = model.rsplit("/", 1)[-1].replace(".gguf", "")
    lower = candidate.lower()
    quant_match = re.search(r"(q\d(?:_[a-z]){1,2})", lower)
    quant = quant_match.group(1).upper() if quant_match else ""
    families = (
        ("mixtral-8x7b", "Mixtral-8x7B"),
        ("yi-34b", "Yi-34B"),
        ("deepseek-coder-33b", "DeepSeek-Coder-33B"),
        ("hermes-3-llama-3.1-8b", "Hermes-3-Llama-3.1-8B"),
        ("hermes-3-llama-3-1-8b", "Hermes-3-Llama-3.1-8B"),
    )
    for needle, label in families:
        if needle in lower:
            return f"{label} {quant}".strip()
    return candidate[:38] + ("..." if len(candidate) > 38 else "")


def _readiness_panel(
    theme: Theme,
    memory_status: str,
    provider_status: str,
    active_theme: str,
    last_verdict: str,
    session_id: str,
    lifecycle_state: str,
) -> ft.Control:
    provider = provider_status.upper()
    provider_color = theme.primary_color if provider == "READY" else theme.warning_color
    label_color = theme.panel_label or theme.secondary_text or theme.secondary_color
    value_color = theme.panel_value or theme.text_color
    muted_color = theme.muted_text or theme.secondary_text or theme.secondary_color
    rows = [
        ("SESSION", session_id),
        ("MEMORY", memory_status),
        ("THEME", active_theme.upper()),
        ("PROVIDER", provider),
        ("LAST VERDICT", last_verdict),
        ("LIFECYCLE", lifecycle_state),
    ]
    row_controls = [
        ft.Row(
            [
                ft.Text(
                    _status_glyph(value),
                    color=provider_color if label == "PROVIDER" else theme.accent_color,
                    size=READINESS_ROW_FONT_SIZE,
                    width=10,
                ),
                ft.Text(
                    label,
                    color=label_color,
                    size=READINESS_ROW_FONT_SIZE,
                    width=READINESS_LABEL_WIDTH,
                    no_wrap=True,
                ),
                ft.Text(
                    value,
                    color=provider_color if label == "PROVIDER" else value_color,
                    size=READINESS_ROW_FONT_SIZE,
                    font_family=theme.font_family,
                    weight=ft.FontWeight.BOLD if label in {"PROVIDER", "LAST VERDICT"} else None,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    expand=True,
                ),
            ],
            spacing=3,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        for label, value in rows
    ]
    return ft.Container(
        content=ft.Column(
            [
                ft.Text("TRIBUNAL READINESS", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=11),
                ft.Column(
                    row_controls,
                    spacing=3,
                    expand=True,
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
            ],
            spacing=5,
            expand=True,
            tight=True,
        ),
        padding=8,
        border=ft.border.all(1, label_color),
        bgcolor=theme.surface_color,
        expand=True,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def build_monolith_panel(
    theme: Theme,
    nodes: Dict[str, NodeIdentity],
    statuses: Dict[str, str],
    vote_details: Dict[str, Dict[str, object]] | None = None,
    memory_status: str = "--",
    provider_status: str = "unknown",
    last_verdict: str = "--",
    session_id: str = "--",
    lifecycle_state: str = "IDLE",
    runtime_details: Dict[str, Dict[str, object]] | None = None,
) -> ft.Control:
    cards = []
    vote_details = vote_details or {}
    runtime_details = runtime_details or {}
    muted_color = theme.muted_text or theme.secondary_text or theme.secondary_color
    for key in [*TRIBUNAL_AGENT_IDS, ARBITER]:
        labels = theme.monolith_labels.get(key)
        node_name = labels["node"] if labels else key
        core_name = labels["core"] if labels else "CONTROL CORE"
        status = statuses.get(key, "ONLINE")
        model = nodes[key].model if key in nodes else "operator"
        compact_model = _compact_model_name(model)
        color = status_color(theme, status)
        category = status_color_category(status)
        opacity = 0.55 if category == "error" and status.upper() == "OFFLINE" else 1.0
        details = vote_details.get(key, {})
        detail_lines = []
        runtime = runtime_details.get(key, {})
        active_runtime = bool(runtime.get("active")) if runtime else False
        if runtime:
            activity_state = str(runtime.get("state", "IDLE"))
            glyph = str(runtime.get("glyph", ""))
            pulse = str(runtime.get("pulse", "*"))
            activity = str(runtime.get("activity", activity_state))
            latency_ms = int(runtime.get("latency_ms", 0) or 0)
            signal = str(runtime.get("signal", ""))
            detail_lines.append(
                ft.Text(
                    f"{glyph} {pulse} {activity}".strip(),
                    color=_runtime_color(theme, activity_state),
                    size=9,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )
            detail_lines.append(
                ft.Text(
                    f"LATENCY: {latency_ms}ms {signal}",
                    color=muted_color,
                    size=9,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )
        if details:
            confidence = details.get("confidence")
            evidence_quality = details.get("evidence_quality")
            critical_risk = bool(details.get("critical_risk"))
            response_time = details.get("response_time")
            reasoning = str(details.get("reasoning", "") or "")
            if confidence is not None:
                detail_lines.append(
                    ft.Text(f"confidence {float(confidence):.0%}", color=theme.text_color, size=9, max_lines=1)
                )
            if evidence_quality is not None:
                detail_lines.append(
                    ft.Text(f"evidence {float(evidence_quality):.0%}", color=theme.text_color, size=9, max_lines=1)
                )
            if critical_risk:
                detail_lines.append(ft.Text("critical risk flagged", color=theme.error_color, size=9, max_lines=1))
            if response_time is not None:
                detail_lines.append(
                    ft.Text(f"response {float(response_time):.2f}s", color=theme.text_color, size=9, max_lines=1)
                )
            if reasoning:
                snippet = reasoning[:72] + ("..." if len(reasoning) > 72 else "")
                detail_lines.append(
                    ft.Text(
                        snippet,
                        color=theme.muted_text or theme.secondary_color,
                        size=9,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    )
                )
        detail_lines = detail_lines[:3]
        cards.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    node_name,
                                    color=theme.primary_color if active_runtime else theme.accent_color,
                                    weight=ft.FontWeight.BOLD,
                                    size=15,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(key, color=theme.text_color, size=10, font_family=theme.font_family, max_lines=1),
                                ft.Text(
                                    core_name,
                                    color=theme.secondary_text or theme.secondary_color,
                                    size=9,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    compact_model,
                                    color=muted_color,
                                    size=9,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    tooltip=model,
                                ),
                                *detail_lines,
                            ],
                            spacing=1,
                            expand=True,
                            tight=True,
                        ),
                        ft.Column(
                            [
                                ft.Text(_status_glyph(status), color=color, size=14),
                                ft.Text(status, color=color, weight=ft.FontWeight.BOLD, size=13, max_lines=1),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=0,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=MONOLITH_CARD_PADDING,
                border=ft.border.all(2 if active_runtime else 1, color),
                bgcolor=theme.surface_color,
                opacity=opacity,
                expand=1,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                data={"role": "monolith_card", "agent_id": key, "compact_model": compact_model},
            )
        )
    readiness = _readiness_panel(
        theme,
        memory_status,
        provider_status,
        theme.key,
        last_verdict,
        session_id,
        lifecycle_state,
    )
    return ft.Column(
        [ft.Text("MONOLITH STATUS", color=theme.primary_color, weight=ft.FontWeight.BOLD), *cards, readiness],
        spacing=7,
        expand=True,
    )


__all__ = [
    "READINESS_ROW_LABELS",
    "MONOLITH_CARD_COUNT",
    "build_monolith_panel",
    "status_color",
    "status_color_category",
]
