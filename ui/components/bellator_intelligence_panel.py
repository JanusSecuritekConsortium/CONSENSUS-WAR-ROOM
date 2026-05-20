from __future__ import annotations

from typing import Any, Dict, Iterable, List

import flet as ft

from core.models import Theme


def format_bellator_intelligence_diagnostics(payload: Dict[str, Any] | None) -> List[str]:
    if not isinstance(payload, dict) or not payload.get("available"):
        summary = payload.get("source_diagnostics_summary") if isinstance(payload, dict) else None
        return [
            "PACKET: unavailable",
            f"DIAGNOSTICS: {summary or 'No Bellator Context Packet cache found.'}",
        ]

    enabled = _join(payload.get("enabled_sources"), empty="none")
    unavailable = _join(payload.get("unavailable_sources"), empty="none")
    cache_age = _format_age(payload.get("cache_age_seconds"))
    return [
        f"PACKET: {payload.get('timestamp', '--')}",
        f"ENABLED: {enabled}",
        f"UNAVAILABLE: {unavailable}",
        f"CACHE AGE: {cache_age}",
        f"NORMALIZED EVENTS: {payload.get('normalized_event_count', 0)}",
        f"HIGHEST SEVERITY: {payload.get('highest_severity', 0.0)}",
        f"SOURCES: {payload.get('source_diagnostics_summary', 'No source diagnostics.')}",
    ]


def build_bellator_intelligence_panel(
    theme: Theme,
    diagnostics: Dict[str, Any] | None,
    on_refresh=None,
) -> ft.Control:
    rows = [
        ft.Text(line, color=theme.text_color, font_family=theme.font_family, selectable=True, size=10, max_lines=2)
        for line in format_bellator_intelligence_diagnostics(diagnostics)
    ]
    header_controls: List[ft.Control] = [
        ft.Text("BELLATOR INTELLIGENCE", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=12),
    ]
    if on_refresh is not None:
        header_controls.append(
            ft.TextButton(
                "REFRESH",
                on_click=on_refresh,
                style=ft.ButtonStyle(
                    color=theme.accent_color,
                    shape=ft.RoundedRectangleBorder(radius=0),
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    text_style=ft.TextStyle(size=10, font_family=theme.font_family),
                ),
                height=28,
            )
        )
    return ft.Column(
        [
            ft.Row(header_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            *rows,
        ],
        spacing=3,
    )


def _join(values: Any, empty: str) -> str:
    if isinstance(values, str):
        return values or empty
    if isinstance(values, Iterable):
        text = ", ".join(str(value) for value in values if value)
        return text or empty
    return empty


def _format_age(value: Any) -> str:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return "unknown"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h {seconds % 3600 // 60}m"


__all__ = ["build_bellator_intelligence_panel", "format_bellator_intelligence_diagnostics"]
