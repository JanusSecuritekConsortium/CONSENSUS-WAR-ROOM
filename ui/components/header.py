from __future__ import annotations

import flet as ft

from config.version import SYSTEM_VERSION
from core.models import Theme
from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import HeaderLogoLayout, THEME_GRAPHIC_ASSETS, get_theme_graphic_asset

GUI_HEADER_HEIGHT = 170
COMPACT_LOGO_MAX_LINES = 12
GUI_LOGO_BOX_HEIGHT = GUI_HEADER_HEIGHT - 28
GUI_LOGO_BOX_MAX_WIDTH = 1120
LOGO_FONT_FAMILY = "Consolas"
LOGO_FONT_SIZE = 12
GUI_COMPACT_LOGO_FILES = {key: asset.logo_path for key, asset in THEME_GRAPHIC_ASSETS.items()}


def _read_logo_text_preserved(path) -> str:
    return path.read_bytes().decode("utf-8")


def _logo_width(logo: str) -> int:
    longest = max((len(line) for line in logo.splitlines()), default=64)
    return max(360, min(GUI_LOGO_BOX_MAX_WIDTH, int(longest * 7.5) + 32))


def _logo_box_width(logo: str, layout: HeaderLogoLayout) -> int:
    if layout.logo_box_width is not None:
        return layout.logo_box_width
    calculated = _logo_width(logo)
    if layout.logo_box_max_width is not None:
        return min(layout.logo_box_max_width, calculated)
    return calculated


def _logo_box_height(layout: HeaderLogoLayout) -> int:
    return layout.logo_box_height or GUI_LOGO_BOX_HEIGHT


def theme_header_height(theme: Theme) -> int:
    return header_logo_layout(theme).header_height or GUI_HEADER_HEIGHT


def header_logo_layout(theme: Theme) -> HeaderLogoLayout:
    try:
        return get_theme_graphic_asset(theme.key).header_layout
    except KeyError:
        return HeaderLogoLayout(logo_font_size=LOGO_FONT_SIZE)


def _alignment(layout: HeaderLogoLayout):
    if layout.logo_vertical_align == "top":
        return ft.alignment.top_center
    if layout.logo_vertical_align == "bottom":
        return ft.alignment.bottom_center
    return ft.alignment.center


def _horizontal_alignment(layout: HeaderLogoLayout):
    if layout.logo_horizontal_align == "left":
        return ft.CrossAxisAlignment.START
    if layout.logo_horizontal_align == "right":
        return ft.CrossAxisAlignment.END
    return ft.CrossAxisAlignment.CENTER


def _scroll_mode(layout: HeaderLogoLayout):
    return ft.ScrollMode.AUTO if layout.logo_box_scroll_enabled else None


def _build_logo_text(logo: str, theme: Theme) -> ft.Text:
    font_size = header_logo_layout(theme).logo_font_size
    return ft.Text(
        logo,
        font_family=LOGO_FONT_FAMILY,
        color=theme.primary_color,
        selectable=False,
        no_wrap=True,
        overflow=ft.TextOverflow.VISIBLE,
        style=ft.TextStyle(
            font_family=LOGO_FONT_FAMILY,
            size=font_size,
            height=1.0,
            letter_spacing=0,
            word_spacing=0,
            overflow=ft.TextOverflow.VISIBLE,
        ),
        size=font_size,
        data={"role": "theme_logo_text"},
    )


def system_status_label_color(theme: Theme) -> str:
    if theme.key == "arasaka":
        return theme.secondary_text or "#ff8a8f"
    return theme.secondary_color


def _build_scrollable_logo_content(logo: str, theme: Theme) -> ft.Column:
    layout = header_logo_layout(theme)
    return ft.Column(
        [
            ft.Row(
                [_build_logo_text(logo, theme)],
                spacing=0,
                tight=True,
                wrap=False,
                scroll=_scroll_mode(layout),
                alignment=ft.MainAxisAlignment.CENTER,
            )
        ],
        spacing=0,
        tight=True,
        scroll=_scroll_mode(layout),
        horizontal_alignment=_horizontal_alignment(layout),
    )


def logo_text_control_from_box(logo_box: ft.Container) -> ft.Text:
    content = logo_box.content
    if isinstance(content, ft.Text):
        return content
    return content.controls[0].controls[0]


def compact_logo_text(theme: Theme, max_lines: int = COMPACT_LOGO_MAX_LINES) -> str:
    try:
        dedicated = get_theme_graphic_asset(theme.key).logo_path
    except KeyError:
        dedicated = GUI_COMPACT_LOGO_FILES.get(theme.key)
    if dedicated and dedicated.exists():
        if theme.key in {"eva", "nerv", "helldivers"}:
            return _read_logo_text_preserved(dedicated)
        return read_normalized_logo(dedicated).text
    lines = theme.logo.rstrip("\n").splitlines()
    first_visible = next((index for index, line in enumerate(lines) if line.strip()), 0)
    return "\n".join(lines[first_visible : first_visible + max_lines])


def has_dedicated_gui_compact_logo(theme: Theme) -> bool:
    path = GUI_COMPACT_LOGO_FILES.get(theme.key)
    return bool(path and path.exists())


def build_header(
    theme: Theme,
    provider_status: str,
    memory_status: str,
    session_id: str = "--",
    compact: bool = True,
    ambient_status: str = "MONOLITH LINK STABLE",
    health_badge: dict[str, str] | None = None,
) -> ft.Control:
    logo = compact_logo_text(theme) if compact else theme.logo.rstrip("\n")
    provider = provider_status.upper()
    provider_color = theme.primary_color if provider == "READY" else theme.warning_color
    badge = health_badge or {"label": provider if provider in {"READY", "DEGRADED", "ERROR"} else "DEGRADED", "color_role": "warning"}
    badge_label = str(badge.get("label", "DEGRADED")).upper()
    badge_role = str(badge.get("color_role", "warning"))
    badge_color = {
        "primary": theme.primary_color,
        "warning": theme.warning_color,
        "error": theme.error_color,
    }.get(badge_role, theme.warning_color)
    telemetry = [
        ("BUILD", SYSTEM_VERSION),
        ("ACTIVE MODE", "GUI WAR ROOM"),
        ("ACTIVE THEME", theme.key.upper()),
        ("PROVIDER", provider),
        ("MEMORY", memory_status),
        ("SESSION", session_id),
    ]
    logo_layout = header_logo_layout(theme)
    logo_box_height = _logo_box_height(logo_layout)
    header_height = theme_header_height(theme)
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=_build_scrollable_logo_content(logo, theme),
                    width=_logo_box_width(logo, logo_layout),
                    height=logo_box_height,
                    padding=ft.padding.only(
                        left=logo_layout.logo_side_padding,
                        right=logo_layout.logo_side_padding,
                        top=logo_layout.logo_top_padding,
                        bottom=logo_layout.logo_bottom_padding,
                    ),
                    alignment=_alignment(logo_layout),
                    border=ft.border.all(1, theme.secondary_color),
                    bgcolor=theme.background_color,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("SYSTEM STATUS", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=15),
                                    ft.Container(
                                        content=ft.Text(
                                            f"HEALTH {badge_label}",
                                            color=badge_color,
                                            font_family=theme.font_family,
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        border=ft.border.all(1, badge_color),
                                        bgcolor=theme.background_color,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            *[
                                ft.Row(
                                    [
                                        ft.Text(
                                            label,
                                            color=system_status_label_color(theme),
                                            width=120,
                                            font_family=theme.font_family,
                                            size=12,
                                        ),
                                        ft.Text(
                                            value,
                                            color=provider_color if label == "PROVIDER" else theme.text_color,
                                            font_family=theme.font_family,
                                            size=12,
                                            weight=ft.FontWeight.BOLD if label in {"PROVIDER", "ACTIVE THEME"} else None,
                                        ),
                                    ],
                                    spacing=8,
                                )
                                for label, value in telemetry
                            ],
                            ft.Text(f"* {ambient_status}", color=theme.accent_color, font_family=theme.font_family, size=12),
                        ],
                        spacing=3,
                    ),
                    padding=12,
                    expand=True,
                    height=logo_box_height,
                    border=ft.border.all(1, theme.primary_color),
                    bgcolor=theme.surface_color,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            wrap=False,
        ),
        padding=8,
        height=header_height,
        border=ft.border.all(1, theme.primary_color),
        bgcolor=theme.background_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


__all__ = [
    "GUI_COMPACT_LOGO_FILES",
    "GUI_HEADER_HEIGHT",
    "GUI_LOGO_BOX_HEIGHT",
    "GUI_LOGO_BOX_MAX_WIDTH",
    "LOGO_FONT_FAMILY",
    "LOGO_FONT_SIZE",
    "COMPACT_LOGO_MAX_LINES",
    "build_header",
    "compact_logo_text",
    "header_logo_layout",
    "theme_header_height",
    "has_dedicated_gui_compact_logo",
    "logo_text_control_from_box",
    "system_status_label_color",
]
