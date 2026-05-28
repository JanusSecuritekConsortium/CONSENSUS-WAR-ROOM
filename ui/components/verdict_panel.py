from __future__ import annotations

import flet as ft

from core.models import Theme, TribunalResult
from ui.components.reasoning_stream import build_phase_timeline, build_reasoning_stream, convergence_bar_text
from ui.war_room_runtime import lifecycle_banner_label


def _confidence_color(theme: Theme, value: float) -> str:
    if value >= 0.75:
        return theme.primary_color
    if value >= 0.45:
        return theme.warning_color
    return theme.error_color


def _verdict_color(theme: Theme, verdict: str, confidence: float) -> str:
    normalized = verdict.upper()
    if normalized in {"APPROVE", "APPROVED"}:
        return theme.primary_color
    if normalized in {"DENY", "DENIED", "CAUTION", "ESCALATE", "ERROR"}:
        return theme.error_color
    if normalized in {"NO_CONSENSUS", "ABSTAIN", "DEADLOCK", "HUMAN_REVIEW_REQUIRED", "CONDITIONAL_APPROVAL"}:
        return theme.warning_color
    return _confidence_color(theme, confidence)


def _vote_breakdown(theme: Theme, result: TribunalResult) -> ft.Control:
    rows = []
    for key, vote in result.votes.items():
        labels = theme.monolith_labels.get(key, {"node": key})
        rows.append(
            ft.Row(
                [
                    ft.Text(labels["node"], color=theme.secondary_color, width=190, size=11),
                    ft.Text(vote.vote.value, color=theme.accent_color, width=90, weight=ft.FontWeight.BOLD, size=11),
                    ft.Text(f"{vote.confidence:.0%}", color=theme.text_color, size=11),
                ],
                spacing=8,
            )
        )
    return ft.Column(rows, spacing=2)


def build_verdict_panel(
    theme: Theme,
    result: TribunalResult | None,
    current_proposal: str = "",
    lifecycle_state: str = "IDLE",
    synthesis_text: str = "",
    displayed_confidence: float | None = None,
    prior_decisions_used: int = 0,
    context_summary: str = "",
    cursor_visible: bool = True,
    consensus_locked: bool = False,
    lifecycle_events: list[dict[str, object]] | None = None,
    reasoning_events: list[str] | None = None,
    convergence_percent: float = 0.0,
    phase_durations: dict[str, float] | None = None,
) -> ft.Control:
    if result is None:
        verdict = f"AWAITING PROPOSAL {'_' if cursor_visible else ' '}"
        confidence_value = displayed_confidence or 0.0
        confidence = "--"
        reason = synthesis_text or "NO ACTIVE PROPOSAL\nTRIBUNAL READY FOR DELIBERATION\nALL MONOLITHS SYNCHRONIZED"
        votes = ft.Text("No tribunal vote vector.", color=theme.secondary_color, font_family=theme.font_family, size=11)
    else:
        verdict = f"{result.verdict.value}{'_' if cursor_visible and not consensus_locked else ''}"
        confidence_value = result.confidence if displayed_confidence is None else displayed_confidence
        confidence = f"{confidence_value:.0%}"
        reason = synthesis_text or result.reason
        votes = _vote_breakdown(theme, result)
    lock_text = "[CONSENSUS LOCKED]" if consensus_locked else "CONSENSUS LINK ACTIVE"
    banner = lifecycle_banner_label(lifecycle_state, consensus_locked=consensus_locked)
    confidence_color = _confidence_color(theme, confidence_value)
    verdict_color = _verdict_color(theme, result.verdict.value, confidence_value) if result is not None else theme.primary_color
    banner_color = verdict_color if result is not None else theme.primary_color
    event_stream = lifecycle_events or []
    reasoning_stream = reasoning_events or []
    convergence = max(convergence_percent, confidence_value if result is not None else 0.0)
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("ARBITER VERDICT", color=theme.primary_color, weight=ft.FontWeight.BOLD),
                        ft.Text("LIVE", color=theme.accent_color, font_family=theme.font_family),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    ft.Text(banner, color=banner_color, weight=ft.FontWeight.BOLD, size=12, font_family=theme.font_family),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border=ft.border.all(1, banner_color),
                    bgcolor=theme.background_color,
                ),
                ft.Text(f"LIFECYCLE: {lifecycle_state}", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=12),
                build_phase_timeline(theme, lifecycle_state, event_stream),
                ft.Text(f"CURRENT: {current_proposal or '--'}", color=theme.text_color, size=12),
                ft.Text(verdict, color=verdict_color, weight=ft.FontWeight.BOLD, size=32),
                ft.Text(lock_text, color=theme.primary_color if consensus_locked else theme.secondary_color, size=11, font_family=theme.font_family),
                ft.Row(
                    [
                        ft.Text("CONVERGENCE", color=theme.primary_color, width=140, size=11, weight=ft.FontWeight.BOLD),
                        ft.Text(convergence_bar_text(convergence), color=theme.accent_color, font_family=theme.font_family, size=11),
                    ],
                    spacing=8,
                ),
                ft.Row(
                    [
                        ft.Text(f"CONFIDENCE: {confidence}", color=theme.text_color, width=140),
                        ft.ProgressBar(value=confidence_value, color=confidence_color, bgcolor=theme.background_color, expand=True),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text("TRIBUNAL VECTOR", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=12),
                votes,
                ft.Text("ARBITER SYNTHESIS", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=12),
                ft.Text(reason, color=theme.text_color, selectable=True),
                ft.Text("REASONING STATE", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=12),
                build_reasoning_stream(theme, reasoning_stream),
                ft.Text(f"Context used: {prior_decisions_used} prior decisions", color=theme.secondary_text or theme.secondary_color, size=11),
                ft.Text(context_summary or "No retrieved context.", color=theme.muted_text or theme.secondary_color, size=10, selectable=True),
            ],
            spacing=10,
        ),
        padding=14,
        border=ft.border.all(2, theme.primary_color),
        bgcolor=theme.surface_color,
    )
