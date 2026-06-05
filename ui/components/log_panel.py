from __future__ import annotations

from typing import Iterable

import flet as ft

from core.models import Theme
from ui.components.bellator_intelligence_panel import build_bellator_intelligence_panel
from ui.components.safe_text import safe_ellipsis


def log_level_color_category(line: str) -> str:
    padded = f" {line.upper()} "
    if " ERROR " in padded or " FAIL " in padded:
        return "error"
    if " WARN " in padded or " WARNING " in padded or " DEGRADED " in padded:
        return "warning"
    if " SUCCESS " in padded or " OK " in padded or " PASS " in padded:
        return "success"
    if " DECISION" in padded or " VERDICT" in padded or " VOTE" in padded:
        return "decision"
    if " INFO " in padded:
        return "info"
    return "muted"


def _level_color(theme: Theme, line: str) -> str:
    category = log_level_color_category(line)
    if category == "error":
        return theme.error_color
    if category == "warning":
        return theme.warning_color
    if category == "success":
        return theme.primary_color
    if category == "decision":
        return theme.accent_color
    if category == "info":
        return theme.secondary_color
    return theme.text_color


def compact_log_line(line: str) -> str:
    if "msty_runtime_health" in line:
        prefix = line.split("]", 1)[0] + "]" if "]" in line else "[--:--:--]"
        level = "WARN" if "WARN" in line.upper() else "OK"
        return f"{prefix} HEALTH {level}"
    if " gui_verdict_update" in line or " verdict" in line:
        prefix = line.split("]", 1)[0] + "]" if "]" in line else "[--:--:--]"
        return f"{prefix} CONSENSUS verdict"
    if " vote" in line:
        prefix = line.split("]", 1)[0] + "]" if "]" in line else "[--:--:--]"
        return f"{prefix} VOTE received"
    return line


def _log_rows(theme: Theme, logs: Iterable[str]) -> ft.Control:
    rows = [
        ft.Text(
            safe_ellipsis(compact_log_line(line), 88),
            color=_level_color(theme, line),
            font_family=theme.font_family,
            selectable=True,
            size=11,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        for line in logs
    ]
    return ft.Column(rows or [ft.Text("No recent log events.", color=theme.secondary_color, size=11)], spacing=2)


def _decision_color(theme: Theme, line: str) -> str:
    verdict = line.split("|", 1)[0].strip().upper()
    if verdict in {"APPROVE", "APPROVED"}:
        return theme.primary_color
    if verdict in {"DENY", "DENIED", "ERROR"}:
        return theme.error_color
    if verdict in {"NO_CONSENSUS", "CAUTION", "ESCALATE", "DEADLOCK", "HUMAN_REVIEW_REQUIRED", "CONDITIONAL_APPROVAL"}:
        return theme.warning_color
    return theme.text_color


def _decision_rows(theme: Theme, decisions: Iterable[str]) -> ft.Control:
    rows = [
        ft.Text(
            safe_ellipsis(line, 88),
            color=_decision_color(theme, line),
            font_family=theme.font_family,
            selectable=True,
            size=11,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        for line in decisions
    ]
    return ft.Column(rows or [ft.Text("No recent decisions.", color=theme.secondary_color, size=11)], spacing=3)


def _timeline_rows(theme: Theme, timeline_events: Iterable[str]) -> ft.Control:
    rows = [
        ft.Text(
            safe_ellipsis(line, 96),
            color=theme.accent_color,
            font_family=theme.font_family,
            selectable=True,
            size=10,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        for line in timeline_events
    ]
    return ft.Column(rows or [ft.Text("Timeline standing by.", color=theme.secondary_color, size=10)], spacing=2)


def build_log_panel(
    theme: Theme,
    logs: Iterable[str],
    decisions: Iterable[str],
    timeline_events: Iterable[str] | None = None,
    bellator_intelligence: dict | None = None,
    refresh_bellator_intelligence=None,
) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("LIVE LOGS", color=theme.primary_color, weight=ft.FontWeight.BOLD),
                        ft.Text("TAIL -F", color=theme.accent_color, font_family=theme.font_family, size=11),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                _log_rows(theme, logs),
                ft.Divider(color=theme.secondary_color),
                ft.Text("RECENT DECISIONS", color=theme.accent_color, weight=ft.FontWeight.BOLD),
                _decision_rows(theme, decisions),
                ft.Divider(color=theme.secondary_color),
                build_bellator_intelligence_panel(theme, bellator_intelligence, refresh_bellator_intelligence),
                ft.Divider(color=theme.secondary_color),
                ft.Text("TRIBUNAL TIMELINE", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=12),
                _timeline_rows(theme, timeline_events or []),
            ],
            spacing=7,
            scroll=ft.ScrollMode.AUTO,
            auto_scroll=True,
        ),
        padding=8,
        border=ft.border.all(1, theme.secondary_color),
        bgcolor=theme.surface_color,
        expand=True,
    )


__all__ = ["build_log_panel", "compact_log_line", "log_level_color_category"]
