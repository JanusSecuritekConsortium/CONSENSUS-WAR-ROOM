from __future__ import annotations

from typing import Dict, Iterable, List

import flet as ft

from core.tribunal_events import TRIBUNAL_PHASES
from core.models import Theme


DISPLAY_PHASES = (
    ("CLASSIFYING", "CLASSIFY"),
    ("DISPATCHING", "DISPATCH"),
    ("ANALYZING", "ANALYZE"),
    ("DELIBERATING", "DELIBERATE"),
    ("SYNTHESIZING", "SYNTHESIS"),
    ("CONSENSUS_REACHED", "VERDICT"),
    ("NO_CONSENSUS", "NO CONSENSUS"),
    ("ESCALATION_REQUIRED", "ESCALATE"),
    ("EXPORT_READY", "EXPORT"),
)


def convergence_bar_text(percent: float, width: int = 18) -> str:
    value = max(0.0, min(1.0, float(percent)))
    filled = int(round(value * width))
    return "[" + ("#" * filled).ljust(width, ".") + f"] {value:.0%}"


def build_phase_timeline(theme: Theme, current_phase: str, lifecycle_events: Iterable[Dict[str, object]]) -> ft.Control:
    seen = {str(event.get("phase", "")).upper() for event in lifecycle_events}
    current = current_phase.upper()
    controls: List[ft.Control] = []
    for phase, label in DISPLAY_PHASES:
        if phase not in TRIBUNAL_PHASES:
            continue
        active = phase == current
        complete = phase in seen and not active
        color = theme.primary_color if active else theme.accent_color if complete else (theme.muted_text or theme.secondary_color)
        marker = ">" if active else "*" if complete else "-"
        controls.append(
            ft.Text(
                f"{marker}{label}",
                color=color,
                font_family=theme.font_family,
                size=10,
                weight=ft.FontWeight.BOLD if active else None,
            )
        )
    return ft.Row(controls, spacing=8, wrap=False, scroll=None)


def build_reasoning_stream(theme: Theme, events: Iterable[str], max_lines: int = 5) -> ft.Control:
    visible = list(events)[-max_lines:]
    if not visible:
        visible = ["Tribunal event stream idle."]
    return ft.Column(
        [
            ft.Text(
                f"> {event}",
                color=theme.secondary_text or theme.secondary_color,
                font_family=theme.font_family,
                size=10,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
            for event in visible
        ],
        spacing=2,
        tight=True,
    )
