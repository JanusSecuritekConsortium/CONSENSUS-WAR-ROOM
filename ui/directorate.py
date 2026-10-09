"""Shared DIRECTORATE structure, with existing theme tokens as adapters."""
from __future__ import annotations

import flet as ft
import math
import time

from core.directorate import Directorate, OperationalEvent, DecisionDispatch
from core.models import Theme


def contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        values = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
    a, b = sorted((luminance(foreground), luminance(background)))
    return (b + .05) / (a + .05)


def readable(theme: Theme, color: str) -> str:
    return color if contrast_ratio(color, theme.surface_color) >= 4.5 else theme.text_color


def status_color(theme: Theme, status: str) -> str:
    token = {"AVAILABLE": theme.primary_color, "FAILED": theme.error_color,
             "DEGRADED": theme.warning_color, "RUNNING": theme.accent_color}.get(status, theme.text_color)
    return readable(theme, token)


def event_row(theme: Theme, event: OperationalEvent) -> ft.Control:
    # Reveal complete observed rows, without per-character pauses or blinking.
    return ft.Container(
        ft.Column([
            ft.Text(f"{event.timestamp[11:19]} {event.component} / {event.kind} [{event.status}]",
                    size=12, color=status_color(theme, event.status), font_family=theme.font_family,
                    selectable=True),
            ft.Text(event.summary + (f" / session {event.session_id}" if event.session_id else ""),
                    size=12, color=theme.text_color, font_family=theme.font_family, selectable=True),
        ], spacing=2, tight=True),
        padding=ft.padding.symmetric(vertical=5, horizontal=4),
        data={"role": "directorate_event", "kind": event.kind, "status": event.status},
    )


def button(theme: Theme, label: str, callback, *, disabled: bool = False) -> ft.TextButton:
    return ft.TextButton(label, on_click=callback, disabled=disabled, height=40,
                         style=ft.ButtonStyle(color=readable(theme, theme.accent_color),
                                              shape=ft.RoundedRectangleBorder(radius=0),
                                              text_style=ft.TextStyle(font_family=theme.font_family, size=12)))


PAPER = "#eee6d2"
PAPER_EDGE = "#ddd3ba"
INK = "#272b24"
RULE = "#817964"
STAMP_COLORS = {"APPROVE": "#24552e", "DENY": "#8b2923"}


def stamp(verdict: str) -> tuple[str, str]:
    normalized = {"APPROVED": "APPROVE", "DENIED": "DENY", "DEADLOCK": "NO_CONSENSUS"}.get(verdict, verdict)
    label = {"APPROVE": "APPROVED", "DENY": "DENIED"}.get(normalized, normalized.replace("_", " "))
    return label, STAMP_COLORS.get(normalized, "#745013")


def paper_text(value: str, *, size: int = 12, bold: bool = False, color: str = INK) -> ft.Text:
    return ft.Text(value, color=color, font_family="Consolas", size=size,
                   selectable=True, weight=ft.FontWeight.BOLD if bold else None)


def build_activity(theme: Theme, journal: Directorate, collapsed: bool, toggle=None,
                   open_boot=None) -> ft.Control:
    """Small dispatch preview, with no duplicated startup/vitals feed."""
    dispatches = journal.dispatches()
    latest = dispatches[-1] if dispatches else None
    controls = [ft.Row([
        button(theme, f"{'+' if collapsed else '-'} DIRECTORATE ({len(dispatches)})", toggle),
        button(theme, "OPEN", open_boot),
    ], wrap=True, spacing=0)]
    if not collapsed:
        if latest:
            label, color = stamp(latest.verdict)
            lines = [paper_text(f"DISPATCH {latest.number:04d} / {latest.timestamp[:19]}", size=10),
                     paper_text(label, bold=True, color=color),
                     ft.Divider(color=RULE), paper_text(latest.report, size=11)]
        else:
            lines = [paper_text("DIRECTORATE / DISPATCH DESK", bold=True),
                     paper_text("The next tribunal decision will be printed here.")]
        notices = journal.notices()
        if notices:
            lines.append(paper_text(f"NOTICE / {notices[-1].summary}", size=10))
        controls.append(ft.Container(ft.Column(lines, spacing=5, tight=True,
                                                scroll=ft.ScrollMode.AUTO, auto_scroll=False),
                                     height=260 if latest else None,
                                     padding=12, bgcolor=PAPER, border=ft.border.all(1, RULE),
                                     data={"role": "directorate_unfolded"}))
    return ft.Container(ft.Column(controls, tight=True, spacing=2), padding=8,
                        border=ft.border.all(1, theme.primary_color), bgcolor=theme.surface_color,
                        data={"role": "directorate_activity", "theme": theme.key})


def dispatch_body(dispatch: DecisionDispatch, *, animation: bool, reduced_motion: bool,
                  now: float) -> str:
    lines = dispatch.report.splitlines()[3:]
    if animation and not reduced_motion:
        # Whole lines arrive over at most three seconds; no fake typing delay
        # changes the recorded report, clipboard or export.
        fraction = min(1.0, max(0.0, now - dispatch.received_at) / 3)
        count = min(len(lines), max(6, math.ceil(len(lines) * fraction)))
        lines = lines[:count]
    return "\n".join(lines)


def build_dispatch_roll(journal: Directorate, *, animation: bool = True,
                        reduced_motion: bool = False, now: float | None = None) -> ft.Column:
    now = time.monotonic() if now is None else now
    entries = [(d.timestamp, "dispatch", d) for d in journal.dispatches()]
    entries.extend((n.timestamp, "notice", n) for n in journal.notices())
    controls = [paper_text("CONSENSUS / OFFICIAL DECISION REGISTER", bold=True, size=14),
                paper_text("CURRENT DESKTOP SESSION · Previous decisions remain in History.", size=10),
                ft.Divider(color=RULE, thickness=2)]
    if not entries:
        controls.extend([paper_text("TRANSMISSION STANDBY", bold=True),
                         paper_text("Submit a proposal. The ruling, individual votes, dissent and conditions will appear here.")])
    for _, kind, entry in sorted(entries, key=lambda row: row[0]):
        if kind == "dispatch":
            label, color = stamp(entry.verdict)
            controls.extend([
                paper_text(f"DISPATCH {entry.number:04d} / {entry.timestamp}", bold=True),
                ft.Container(paper_text(label, size=20, bold=True, color=color),
                             border=ft.border.all(2, color), padding=ft.padding.symmetric(horizontal=12, vertical=6),
                             alignment=ft.alignment.center_left,
                             data={"role": "directorate_stamp", "verdict": entry.verdict}),
                paper_text(dispatch_body(entry, animation=animation, reduced_motion=reduced_motion, now=now)),
                ft.Divider(color=RULE, thickness=2),
            ])
        else:
            controls.extend([paper_text(f"OPERATIONAL NOTICE / {entry.timestamp}", size=10, bold=True),
                             paper_text(f"{entry.component} / {entry.kind.replace('_', ' ')}\n{entry.summary}"),
                             ft.Divider(color=RULE)])
    return ft.Column(controls, spacing=12, scroll=ft.ScrollMode.AUTO, auto_scroll=False,
                     expand=True, data={"role": "directorate_roll"})


def build_dispatch_actions(theme: Theme, journal: Directorate, copy=None, export=None,
                           open_history=None) -> ft.Column:
    has_dispatch = bool(journal.dispatches())
    return ft.Column([ft.Row([
        button(theme, "COPY LATEST DISPATCH", copy, disabled=not has_dispatch),
        button(theme, "EXPORT LATEST DISPATCH", export, disabled=not has_dispatch),
        button(theme, "HISTORY", open_history)], wrap=True, spacing=4)], spacing=0, tight=True)


def build_dispatch_desk(theme: Theme, journal: Directorate, roll: ft.Column,
                        close=None, copy=None, export=None, open_history=None, actions=None) -> ft.Control:
    def rail():
        return ft.Container(ft.Column([
            ft.Text("●", color=theme.background_color, size=10) for _ in range(18)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=24, padding=ft.padding.symmetric(vertical=12), bgcolor=PAPER_EDGE)
    return ft.Container(ft.Column([
        ft.Row([ft.Column([ft.Text("DIRECTORATE", size=22, weight=ft.FontWeight.BOLD,
                                   color=readable(theme, theme.primary_color), font_family="Consolas"),
                           ft.Text("TRIBUNAL DISPATCH DESK", size=11, color=theme.text_color, font_family="Consolas")], spacing=0, expand=True),
                button(theme, "CLOSE", close)], spacing=12),
        ft.Container(ft.Row([rail(), ft.Container(roll, padding=20, expand=True), rail()],
                            spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
                     bgcolor=PAPER, expand=True, border=ft.border.symmetric(horizontal=ft.BorderSide(2, RULE))),
        actions if actions is not None else build_dispatch_actions(theme, journal, copy, export, open_history),
        ft.Text("Decisions and recorded conditions · Technical checks: Diagnostics → System Checks",
                color=theme.text_color, size=11, font_family="Consolas"),
    ], expand=True, spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        padding=20, bgcolor=theme.surface_color, border=ft.border.all(1, theme.primary_color),
        data={"role": "directorate_desk"})


def build_boot(theme: Theme, journal: Directorate, busy: bool, retry=None, proceed=None,
               animation: bool = True, reduced_motion: bool = False,
               change_animation=None, change_motion=None) -> ft.Control:
    checks = journal.checks()
    config_ok = any(e.component == "CONFIG" and e.status == "AVAILABLE" for e in checks)
    interface_ok = any(e.component == "INTERFACE" and e.status == "AVAILABLE" for e in checks)
    controls = [
        ft.Text("DIAGNOSTICS / SYSTEM CHECKS", size=18, weight=ft.FontWeight.BOLD,
                color=readable(theme, theme.primary_color), font_family=theme.font_family),
        ft.Text(f"{theme.display_name} / {journal.startup_status()}", color=theme.text_color,
                size=14, font_family=theme.font_family),
        *([ft.ProgressBar(value=None if animation and not reduced_motion else 0,
                          color=theme.primary_color)] if busy else []),
        ft.Container(ft.Column([event_row(theme, e) for e in checks],
                               scroll=ft.ScrollMode.AUTO, spacing=0), expand=True),
        ft.Checkbox(label="Animate observed changes", value=animation, on_change=change_animation,
                    label_style=ft.TextStyle(color=theme.text_color, font_family=theme.font_family, size=13)),
        ft.Checkbox(label="Reduced motion", value=reduced_motion, on_change=change_motion,
                    label_style=ft.TextStyle(color=theme.text_color, font_family=theme.font_family, size=13)),
        ft.Text("Health checks observe availability; successful generation is checked during deliberation.\n"
                "Prior failures remain in the diagnostics record. Close returns to the war room.",
                color=theme.text_color, size=12, font_family=theme.font_family),
        ft.Row([button(theme, "RETRY CHECKS", retry, disabled=busy),
                button(theme, "CLOSE", proceed, disabled=not config_ok or not interface_ok)], wrap=True),
    ]
    return ft.Container(ft.Column(controls, expand=True, spacing=8), padding=20,
                        border=ft.border.all(1, theme.primary_color), bgcolor=theme.surface_color,
                        data={"role": "directorate_boot"})


def add_cable_controls(panel: ft.Container, theme: Theme, cable: str, enabled: bool,
                       toggle=None, copy=None, export=None, has_result: bool = False) -> ft.Container:
    actions = ft.Row([button(theme, "STANDARD" if enabled else "CABLE VIEW", toggle),
                      button(theme, "COPY CABLE", copy, disabled=not has_result),
                      button(theme, "EXPORT CABLE", export, disabled=not has_result)], wrap=True, spacing=0)
    if enabled:
        panel.content = ft.Column([actions, ft.Text(cable, selectable=True, color=theme.text_color,
                                                   font_family=theme.font_family, size=13)],
                                  scroll=ft.ScrollMode.AUTO, spacing=8)
    else:
        panel.content.controls.insert(1, actions)
    return panel
