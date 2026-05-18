from __future__ import annotations

import flet as ft

from config.version import SYSTEM_VERSION
from core.models import Theme
from core.paths import SYSTEM_ROOT

GUI_HEADER_HEIGHT = 144
COMPACT_LOGO_MAX_LINES = 8
GUI_LOGO_BOX_HEIGHT = GUI_HEADER_HEIGHT - 28
GUI_LOGO_BOX_MAX_WIDTH = 640
GUI_LOGO_DIR = SYSTEM_ROOT / "static" / "logos" / "gui"
GUI_COMPACT_LOGO_FILES = {
    "eva": GUI_LOGO_DIR / "eva_header.txt",
    "nerv": GUI_LOGO_DIR / "eva_header.txt",
    "wh40k": GUI_LOGO_DIR / "wh40k_header.txt",
    "helldivers": GUI_LOGO_DIR / "helldivers_header.txt",
    "arasaka": GUI_LOGO_DIR / "arasaka_header.txt",
    "military": GUI_LOGO_DIR / "military_header.txt",
    "janus": GUI_LOGO_DIR / "janus_header.txt",
}


def _logo_width(logo: str) -> int:
    longest = max((len(line) for line in logo.splitlines()), default=64)
    return max(320, min(GUI_LOGO_BOX_MAX_WIDTH, int(longest * 6.2) + 24))


def _logo_font_size(logo: str) -> int:
    longest = max((len(line) for line in logo.splitlines()), default=64)
    return 8 if longest > 100 else 9


def compact_logo_text(theme: Theme, max_lines: int = COMPACT_LOGO_MAX_LINES) -> str:
    dedicated = GUI_COMPACT_LOGO_FILES.get(theme.key)
    if dedicated and dedicated.exists():
        return dedicated.read_text(encoding="utf-8").rstrip("\n")
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
) -> ft.Control:
    logo = compact_logo_text(theme) if compact else theme.logo.rstrip("\n")
    provider = provider_status.upper()
    provider_color = theme.primary_color if provider == "READY" else theme.warning_color
    telemetry = [
        ("BUILD", SYSTEM_VERSION),
        ("ACTIVE MODE", "GUI WAR ROOM"),
        ("ACTIVE THEME", theme.key.upper()),
        ("PROVIDER", provider),
        ("MEMORY", memory_status),
        ("SESSION", session_id),
    ]
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        logo,
                        font_family=theme.font_family,
                        color=theme.primary_color,
                        selectable=False,
                        no_wrap=True,
                        size=_logo_font_size(logo),
                    ),
                    width=_logo_width(logo),
                    height=GUI_LOGO_BOX_HEIGHT,
                    padding=4,
                    alignment=ft.alignment.center,
                    border=ft.border.all(1, theme.secondary_color),
                    bgcolor=theme.background_color,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("SYSTEM STATUS", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=15),
                            *[
                                ft.Row(
                                    [
                                        ft.Text(
                                            label,
                                            color=theme.secondary_color,
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
                    height=GUI_LOGO_BOX_HEIGHT,
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
        height=GUI_HEADER_HEIGHT,
        border=ft.border.all(1, theme.primary_color),
        bgcolor=theme.background_color,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


__all__ = [
    "GUI_COMPACT_LOGO_FILES",
    "GUI_HEADER_HEIGHT",
    "GUI_LOGO_BOX_HEIGHT",
    "GUI_LOGO_BOX_MAX_WIDTH",
    "COMPACT_LOGO_MAX_LINES",
    "build_header",
    "compact_logo_text",
    "has_dedicated_gui_compact_logo",
]
