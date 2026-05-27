from __future__ import annotations

from typing import Callable, Iterable, Mapping

import flet as ft

from core.models import Theme


EMPTY_PROPOSAL_HINT = "Awaiting proposal. Select a template or enter a tribunal query."


def build_proposal_panel(
    theme: Theme,
    on_submit: Callable[[str], None],
    *,
    initial_value: str = "",
    templates: Iterable[Mapping[str, str]] | None = None,
    selected_template_id: str = "",
    on_template_select: Callable[[str], None] | None = None,
    on_change: Callable[[str], None] | None = None,
) -> ft.Control:
    template_options = list(templates or [])

    def handle_template_change(event: ft.ControlEvent) -> None:
        if on_template_select is not None:
            on_template_select(str(event.control.value or ""))

    def handle_change(event: ft.ControlEvent) -> None:
        if on_change is not None:
            on_change(str(event.control.value or ""))

    proposal_input = ft.TextField(
        label="Proposal",
        value=initial_value,
        hint_text="Enter tribunal proposal...",
        helper_text="CTRL+ENTER = Submit to Tribunal",
        multiline=True,
        min_lines=5,
        max_lines=8,
        border_color=theme.primary_color,
        focused_border_color=theme.accent_color,
        cursor_color=theme.accent_color,
        color=theme.text_color,
        bgcolor=theme.background_color,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        text_style=ft.TextStyle(font_family=theme.font_family, size=13),
        hint_style=ft.TextStyle(color=theme.muted_text or theme.secondary_color, font_family=theme.font_family),
        helper_style=ft.TextStyle(color=theme.secondary_text or theme.secondary_color, font_family=theme.font_family, size=10),
        on_change=handle_change if on_change is not None else None,
    )

    def handle_submit(_: ft.ControlEvent) -> None:
        on_submit(proposal_input.value or "")

    controls: list[ft.Control] = [
        ft.Text("PROPOSAL", color=theme.primary_color, weight=ft.FontWeight.BOLD),
    ]
    if template_options:
        controls.append(
            ft.Dropdown(
                label="Proposal Template",
                value=selected_template_id or None,
                options=[
                    ft.dropdown.Option(str(item["id"]), str(item["title"]))
                    for item in template_options
                ],
                on_change=handle_template_change if on_template_select is not None else None,
                border_color=theme.secondary_color,
                focused_border_color=theme.accent_color,
                color=theme.text_color,
                bgcolor=theme.background_color,
                text_style=ft.TextStyle(font_family=theme.font_family, size=11),
                label_style=ft.TextStyle(color=theme.secondary_color, font_family=theme.font_family, size=10),
            )
        )
    controls.extend(
        [
            proposal_input,
            ft.Text(
                EMPTY_PROPOSAL_HINT,
                color=theme.secondary_text or theme.secondary_color,
                size=10,
                font_family=theme.font_family,
            ),
            ft.TextButton(
                "SUBMIT TO TRIBUNAL",
                on_click=handle_submit,
                style=ft.ButtonStyle(
                    color=theme.primary_color,
                    bgcolor=theme.background_color,
                    side=ft.BorderSide(1, theme.primary_color),
                    shape=ft.RoundedRectangleBorder(radius=0),
                    padding=ft.padding.symmetric(horizontal=18, vertical=12),
                ),
            ),
        ]
    )

    return ft.Container(
        content=ft.Column(
            controls,
            spacing=7,
            tight=True,
        ),
        padding=ft.padding.only(left=8, right=8, top=7, bottom=10),
        border=ft.border.all(1, theme.secondary_color),
        bgcolor=theme.surface_color,
    )


__all__ = ["EMPTY_PROPOSAL_HINT", "build_proposal_panel"]
