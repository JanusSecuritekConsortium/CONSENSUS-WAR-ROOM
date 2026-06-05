from __future__ import annotations

import flet as ft

from config.version import SYSTEM_VERSION
from core.models import Theme
from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import HeaderLogoLayout, HeaderLogoProfile, THEME_GRAPHIC_ASSETS, get_theme_graphic_asset
from ui.components.safe_text import safe_ellipsis
from ui.components.telemetry_panel import telemetry_graph_lines, telemetry_summary_lines

GUI_HEADER_HEIGHT = 190
COMPACT_LOGO_MAX_LINES = 12
GUI_LOGO_BOX_HEIGHT = GUI_HEADER_HEIGHT - 28
GUI_LOGO_BOX_MAX_WIDTH = 1120
LOGO_FONT_FAMILY = "Consolas"
LOGO_FONT_SIZE = 12
GUI_COMPACT_LOGO_FILES = {key: asset.logo_path for key, asset in THEME_GRAPHIC_ASSETS.items()}
HEADER_TELEMETRY_LIMITS = {
    "wh40k": {"summary": 5, "graph": 1, "value_size": 12, "graph_size": 11, "title_size": 13},
    "default": {"summary": 5, "graph": 1, "value_size": 11, "graph_size": 10, "title_size": 12},
}
HEADER_TELEMETRY_HEIGHT = 132
HEADER_STATUS_TEXT_SIZES = {
    "default": {"title": 17, "row": 12, "ambient": 11},
}


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


def header_logo_profile(theme: Theme) -> HeaderLogoProfile:
    try:
        asset = get_theme_graphic_asset(theme.key)
        if asset.header_profile is not None:
            return asset.header_profile
    except KeyError:
        pass
    return HeaderLogoProfile(max_width=96, max_height=10)


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
            ft.Container(
                ft.Row(
                    [_build_logo_text(logo, theme)],
                    spacing=0,
                    tight=True,
                    wrap=False,
                    scroll=_scroll_mode(layout),
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                margin=ft.margin.only(left=layout.logo_offset_x, top=layout.logo_offset_y),
            ),
        ],
        spacing=0,
        tight=True,
        scroll=_scroll_mode(layout),
        horizontal_alignment=_horizontal_alignment(layout),
    )


def _logo_fits_header_box(logo: str, layout: HeaderLogoLayout) -> bool:
    lines = logo.splitlines()
    if not lines:
        return False
    width = max((len(line) for line in lines), default=0)
    available_width = (_logo_box_width(logo, layout) - (layout.logo_side_padding * 2))
    available_height = (_logo_box_height(layout) - layout.logo_top_padding - layout.logo_bottom_padding)
    estimated_width = width * max(1, layout.logo_font_size) * 0.62
    estimated_height = len(lines) * max(1, layout.logo_font_size)
    return estimated_width <= available_width and estimated_height <= available_height


def _header_logo_variant_paths(theme: Theme) -> list:
    asset = get_theme_graphic_asset(theme.key)
    base = asset.logo_path
    stem = base.stem
    suffix = base.suffix
    return [
        base,
        base.with_name(f"{stem}_compact{suffix}"),
        base.with_name(f"{stem}_micro{suffix}"),
    ]


def header_logo_text(theme: Theme, compact: bool = True) -> str:
    layout = header_logo_layout(theme)
    try:
        paths = _header_logo_variant_paths(theme)
    except KeyError:
        return compact_logo_text(theme) if compact else theme.logo.rstrip("\n")
    for index, path in enumerate(paths):
        if index > 0 and not path.exists():
            continue
        if not path.exists():
            continue
        logo = _read_logo_text_preserved(path) if theme.key in {"eva", "nerv", "helldivers"} else read_normalized_logo(path).text
        if _logo_fits_header_box(logo, layout):
            return logo
    return "[LOGO TOO LARGE]"


def logo_text_control_from_box(logo_box: ft.Container) -> ft.Text:
    def walk(control) -> ft.Text | None:
        if isinstance(control, ft.Text) and getattr(control, "data", {}).get("role") == "theme_logo_text":
            return control
        content = getattr(control, "content", None)
        if content is not None:
            found = walk(content)
            if found is not None:
                return found
        for child in getattr(control, "controls", []) or []:
            found = walk(child)
            if found is not None:
                return found
        return None

    found = walk(logo_box)
    if found is None:
        raise ValueError("Logo text control not found")
    return found


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


def _bounded_telemetry(theme_key: str, telemetry: dict | None) -> tuple[list[str], list[str], int, int]:
    profile = HEADER_TELEMETRY_LIMITS.get(theme_key, HEADER_TELEMETRY_LIMITS["default"])
    summary_limit = int(profile["summary"])
    graph_limit = int(profile["graph"])
    summary = [safe_ellipsis(line, 58) for line in telemetry_summary_lines(theme_key, telemetry)]
    graph = [safe_ellipsis(line, 72) for line in telemetry_graph_lines(theme_key, telemetry)]
    summary_truncated = len(summary) > summary_limit
    graph_truncated = len(graph) > graph_limit
    summary = summary[:summary_limit]
    graph = graph[:graph_limit]
    if summary_truncated and summary:
        summary[-1] = safe_ellipsis(summary[-1], 54) + " ..."
    if graph_truncated and graph:
        graph[-1] = safe_ellipsis(graph[-1], 68) + " ..."
    return summary, graph, int(profile["value_size"]), int(profile["graph_size"])


def _telemetry_title_size(theme_key: str) -> int:
    profile = HEADER_TELEMETRY_LIMITS.get(theme_key, HEADER_TELEMETRY_LIMITS["default"])
    return int(profile.get("title_size", HEADER_TELEMETRY_LIMITS["default"]["title_size"]))


def _header_status_sizes(theme_key: str) -> dict[str, int]:
    return HEADER_STATUS_TEXT_SIZES.get(theme_key, HEADER_STATUS_TEXT_SIZES["default"])


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
    telemetry: dict | None = None,
) -> ft.Control:
    logo = header_logo_text(theme, compact=compact)
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
    status_rows = [
        ("BUILD", SYSTEM_VERSION),
        ("ACTIVE MODE", "GUI WAR ROOM"),
        ("ACTIVE THEME", theme.key.upper()),
        ("PROVIDER", provider),
        ("MEMORY", memory_status),
    ]
    status_rows.append(("SESSION", session_id))
    telemetry_lines, telemetry_graph, telemetry_value_size, telemetry_graph_size = _bounded_telemetry(theme.key, telemetry)
    telemetry_title_size = _telemetry_title_size(theme.key)
    status_sizes = _header_status_sizes(theme.key)
    logo_layout = header_logo_layout(theme)
    logo_profile = header_logo_profile(theme)
    header_height = theme_header_height(theme)
    logo_box_height = _logo_box_height(logo_layout)
    status_panel_height = header_height - 16
    telemetry_panel_height = min(HEADER_TELEMETRY_HEIGHT, max(100, status_panel_height - 42))
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
                        top=max(logo_layout.logo_top_padding, logo_profile.padding_top),
                        bottom=max(logo_layout.logo_bottom_padding, logo_profile.padding_bottom),
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
                                    ft.Text("SYSTEM STATUS", color=theme.primary_color, weight=ft.FontWeight.BOLD, size=status_sizes["title"]),
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
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            *[
                                                ft.Row(
                                                    [
                                                        ft.Text(
                                                            label,
                                                            color=system_status_label_color(theme),
                                                            width=116,
                                                            font_family=theme.font_family,
                                                            size=status_sizes["row"],
                                                        ),
                                                        ft.Text(
                                                            value,
                                                            color=provider_color if label == "PROVIDER" else theme.text_color,
                                                            font_family=theme.font_family,
                                                            size=status_sizes["row"],
                                                            weight=ft.FontWeight.BOLD if label in {"PROVIDER", "ACTIVE THEME"} else None,
                                                            max_lines=1,
                                                            overflow=ft.TextOverflow.ELLIPSIS,
                                                        ),
                                                    ],
                                                    spacing=8,
                                                )
                                                for label, value in status_rows
                                            ],
                                            ft.Text(
                                                safe_ellipsis(f"* {ambient_status}", 72),
                                                color=theme.accent_color,
                                                font_family=theme.font_family,
                                                size=status_sizes["ambient"],
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                        ],
                                        spacing=1,
                                        tight=True,
                                        expand=1,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text("LIVE TELEMETRY", color=theme.accent_color, font_family=theme.font_family, size=telemetry_title_size, weight=ft.FontWeight.BOLD),
                                                *[
                                                    ft.Text(line, color=theme.panel_value or theme.text_color, font_family=theme.font_family, size=telemetry_value_size, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                                                    for line in telemetry_lines
                                                ],
                                                *[
                                                    ft.Text(line, color=theme.secondary_text or theme.secondary_color, font_family=theme.font_family, size=telemetry_graph_size, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                                                    for line in telemetry_graph
                                                ],
                                            ],
                                            spacing=1,
                                            tight=True,
                                        ),
                                        width=460,
                                        height=telemetry_panel_height,
                                        padding=ft.padding.only(left=10),
                                        border=ft.border.only(left=ft.BorderSide(1, theme.secondary_color)),
                                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                        data={
                                            "role": "header_telemetry_panel",
                                            "summary_lines": len(telemetry_lines),
                                            "graph_lines": len(telemetry_graph),
                                            "bounded": True,
                                        },
                                    ),
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.START,
                            ),
                        ],
                        spacing=2,
                    ),
                    padding=ft.padding.only(left=12, right=12, top=8, bottom=12),
                    expand=True,
                    height=status_panel_height,
                    border=ft.border.all(1, theme.primary_color),
                    bgcolor=theme.surface_color,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    data={"role": "header_status_panel", "content_vertical_offset": "raised"},
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
    "HEADER_TELEMETRY_HEIGHT",
    "build_header",
    "compact_logo_text",
    "header_logo_profile",
    "header_logo_text",
    "header_logo_layout",
    "theme_header_height",
    "has_dedicated_gui_compact_logo",
    "logo_text_control_from_box",
    "system_status_label_color",
]
