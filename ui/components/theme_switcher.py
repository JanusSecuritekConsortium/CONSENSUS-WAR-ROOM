from __future__ import annotations

from typing import Callable

import flet as ft

from core.models import Theme
from ui.themes.catalog import get_gui_theme_key, get_gui_theme_options

THEME_SWITCHER_WIDTH = 260


def build_theme_switcher(
    theme: Theme,
    on_change: Callable[[str], None],
    on_interaction: Callable[[], None] | None = None,
) -> ft.Control:
    def mark_interaction() -> None:
        if on_interaction is not None:
            on_interaction()

    def handle_change(event: ft.ControlEvent) -> None:
        mark_interaction()
        if event.control.value:
            on_change(str(event.control.value))

    return ft.Dropdown(
        label="THEME",
        value=get_gui_theme_key(theme.key),
        options=[ft.dropdown.Option(option.key, text=option.display_name) for option in get_gui_theme_options()],
        on_change=handle_change,
        on_focus=lambda _: mark_interaction(),
        on_blur=lambda _: mark_interaction(),
        border_color=theme.primary_color,
        focused_border_color=theme.accent_color,
        bgcolor=theme.surface_color,
        color=theme.text_color,
        dense=True,
        width=THEME_SWITCHER_WIDTH,
        menu_width=320,
        text_size=12,
        label_style=ft.TextStyle(color=theme.secondary_color, size=10, font_family=theme.font_family),
        text_style=ft.TextStyle(color=theme.text_color, size=12, font_family=theme.font_family),
        border_radius=0,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
    )


__all__ = ["THEME_SWITCHER_WIDTH", "build_theme_switcher"]
