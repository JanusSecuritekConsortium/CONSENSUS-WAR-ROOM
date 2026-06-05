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
    is_arasaka = theme.key == "arasaka"
    dropdown_bg = "#070707" if is_arasaka else theme.background_color
    dropdown_fill = "#0f0f0f" if is_arasaka else theme.background_color
    dropdown_focus = "#260407" if is_arasaka else theme.surface_color
    dropdown_text = theme.text_color
    dropdown_label = theme.panel_label or theme.secondary_color

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
        dense=True,
        multiline=True,
        min_lines=5,
        max_lines=7,
        border_color=theme.primary_color,
        focused_border_color=theme.accent_color,
        cursor_color=theme.accent_color,
        color=theme.text_color,
        bgcolor=theme.background_color,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        text_style=ft.TextStyle(font_family=theme.font_family, size=13),
        hint_style=ft.TextStyle(color=theme.muted_text or theme.secondary_color, font_family=theme.font_family),
        on_change=handle_change if on_change is not None else None,
        data={"role": "proposal_input"},
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
                dense=True,
                options=[
                    ft.dropdown.Option(
                        str(item["id"]),
                        str(item["title"]),
                        content=ft.Text(
                            str(item["title"]),
                            color=dropdown_text,
                            bgcolor=dropdown_bg,
                            font_family=theme.font_family,
                            size=11,
                        ),
                        text_style=ft.TextStyle(color=dropdown_text, font_family=theme.font_family, size=11),
                    )
                    for item in template_options
                ],
                on_change=handle_template_change if on_template_select is not None else None,
                border_color=theme.secondary_color,
                focused_border_color=theme.accent_color,
                color=dropdown_text,
                focused_color=dropdown_text,
                bgcolor=dropdown_bg,
                fill_color=dropdown_fill,
                focused_bgcolor=dropdown_focus,
                hover_color=dropdown_focus,
                text_style=ft.TextStyle(color=dropdown_text, font_family=theme.font_family, size=11),
                label_style=ft.TextStyle(color=dropdown_label, font_family=theme.font_family, size=10),
                data={
                    "role": "proposal_template_dropdown",
                    "contrast": "arasaka_dark_red" if is_arasaka else "theme_default",
                    "selected_state_color": dropdown_focus if is_arasaka else theme.surface_color,
                },
            )
        )
    controls.extend(
        [
            proposal_input,
            ft.Text(
                f"{EMPTY_PROPOSAL_HINT}  CTRL+ENTER = Submit.",
                color=theme.secondary_text or theme.secondary_color,
                size=10,
                font_family=theme.font_family,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.TextButton(
                "SUBMIT TO TRIBUNAL",
                on_click=handle_submit,
                style=ft.ButtonStyle(
                    color=theme.primary_color,
                    bgcolor=theme.background_color,
                    side=ft.BorderSide(1, theme.primary_color),
                    shape=ft.RoundedRectangleBorder(radius=0),
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                ),
                height=36,
                data={"role": "submit_to_tribunal_button"},
            ),
        ]
    )

    return ft.Container(
        content=ft.Column(
            controls,
            spacing=5,
            tight=True,
        ),
        padding=ft.padding.only(left=10, right=10, top=8, bottom=8),
        border=ft.border.all(1, theme.secondary_color),
        bgcolor=theme.surface_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={"role": "proposal_panel"},
    )


__all__ = ["EMPTY_PROPOSAL_HINT", "build_proposal_panel"]
