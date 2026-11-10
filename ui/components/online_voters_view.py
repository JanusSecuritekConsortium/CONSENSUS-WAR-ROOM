"""The Online voters screen (Ctrl+O): pick each voter's online model, see whether it is ready, and test it."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import flet as ft

from core.llm import online
from core.models import Theme

ROLES = {
    "RATIONALIS": "logic and evidence",
    "AETERNUM": "long-term and history",
    "BELLATOR": "security and risk",
    "BACKUP": "used when a voter's own online model fails",
}


def _light(theme: Theme, ready: Optional[bool]) -> str:
    if ready is None:
        return theme.secondary_color
    return theme.primary_color if ready else theme.error_color


def _options(theme: Theme, value: str) -> List[ft.dropdown.Option]:
    choices = list(online.CHOICES)
    if value and value not in {key for key, _ in choices}:
        choices.append((value, value))  # a hand-written setting stays selectable
    return [ft.dropdown.Option(key or "local", label) for key, label in choices]


def _row(theme: Theme, row: Dict[str, Any], test_result: Optional[str], testing: bool,
         on_choose: Callable[[str, str], None] | None, on_test: Callable[[str], None] | None) -> ft.Control:
    key = row["key"]
    state = row["state"]
    if row["overridden"]:
        state += " (set by the environment; this screen cannot change it)"
    picker = ft.Dropdown(
        value=row["value"] or "local",
        options=_options(theme, row["value"]),
        dense=True,
        width=300,
        disabled=row["overridden"],
        text_style=ft.TextStyle(color=theme.text_color, font_family=theme.font_family, size=12),
        border_color=theme.secondary_color,
        on_change=(lambda event, key=key: on_choose(key, "" if event.control.value == "local" else event.control.value))
        if on_choose else None,
        data={"role": "online_voter_choice", "key": key},
    )
    test = ft.TextButton(
        "TESTING..." if testing else "TEST",
        on_click=(lambda _, key=key: on_test(key)) if on_test else None,
        disabled=testing or not row["ready"],
        style=ft.ButtonStyle(color=theme.accent_color, shape=ft.RoundedRectangleBorder(radius=0)),
        data={"role": "online_voter_test", "key": key},
    )
    details = [ft.Text(f"● {state}", color=_light(theme, row["ready"]), size=11,
                       font_family=theme.font_family)]
    if test_result:
        details.append(ft.Text(test_result, color=theme.text_color, size=10, font_family=theme.font_family,
                               selectable=True))
    return ft.Container(
        ft.Row(
            [
                ft.Column([ft.Text(key, color=theme.primary_color, weight=ft.FontWeight.BOLD,
                                   font_family=theme.font_family),
                           ft.Text(ROLES.get(key, ""), color=theme.text_color, size=10, italic=True)],
                          spacing=2, width=210),
                picker,
                test,
                ft.Column(details, spacing=2, expand=True),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(vertical=8, horizontal=4),
        border=ft.border.only(bottom=ft.BorderSide(1, theme.secondary_color)),
        data={"role": "online_voter_row", "key": key},
    )


def build_online_voters_overlay(theme: Theme, rows: List[Dict[str, Any]], *, test_results: Dict[str, str],
                                testing: set, message: str = "", on_choose=None, on_test=None,
                                on_toggle=None, on_close=None) -> ft.Control:
    enabled = online.online_enabled()
    button_style = ft.ButtonStyle(color=theme.accent_color, shape=ft.RoundedRectangleBorder(radius=0))
    return ft.Column(
        [
            ft.Row([
                ft.Text("ONLINE VOTERS", color=theme.primary_color, weight=ft.FontWeight.BOLD, expand=True),
                ft.TextButton("CLOSE", on_click=on_close, style=button_style),
            ]),
            ft.Text("Each voter can answer with an online model instead of its local Msty model. If the online "
                    "model fails, the voter tries the backup, then its local model. Changes apply to the next "
                    "deliberation.", color=theme.text_color, size=11),
            *[_row(theme, row, test_results.get(row["key"]), row["key"] in testing, on_choose, on_test)
              for row in rows],
            ft.Text(message, color=theme.warning_color, size=11, visible=bool(message),
                    data={"role": "online_voters_message"}),
            ft.Text("Subscriptions need their app signed in once (claude, codex login, grok login). Paid APIs need "
                    "their key in the .env file. Your personal vault brief is "
                    f"{'sent' if online.share_personal_context() else 'never sent'} to online models. Up to "
                    f"{online.token_budget():,} online tokens per deliberation.",
                    color=theme.text_color, size=10, italic=True),
            # Bottom left, away from CLOSE: the master switch sends every voter back to its local model.
            ft.Row([
                ft.Switch(label="All online models on" if enabled else "All online models off (every voter local)",
                          value=enabled, active_color=theme.primary_color,
                          label_style=ft.TextStyle(color=theme.text_color, size=11),
                          on_change=(lambda event: on_toggle(bool(event.control.value))) if on_toggle else None,
                          data={"role": "online_voters_switch"}),
            ], alignment=ft.MainAxisAlignment.START),
        ],
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        data={"role": "online_voters_overlay"},
    )
