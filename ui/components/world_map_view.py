"""ASCII world map controls: the mini map in the BELLATOR panel and the full-screen map (Ctrl+M)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import flet as ft

from core.intelligence.strategic_regions import STRATEGIC_REGIONS
from core.intelligence.world_map import kind_runs, render_world_map
from core.models import Theme

MINI_SIZE = (76, 20)
BIG_SIZE = (240, 58)  # characters; more cells keep countries apart across narrow seas
LEGEND = "x/X BELLATOR feed event   + * # GDELT news: low / medium / high severity   +--+ strategic region"


LAND_FALLBACK = "#8a8a8a"  # neutral grey for themes whose secondary colour vanishes on their background
MIN_LAND_CONTRAST = 3.0


def _luminance(colour: str) -> float:
    value = colour.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float:
    """WCAG contrast ratio between two #rrggbb colours (1 = none, 21 = black on white)."""
    light, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def land_colour(theme: Theme) -> str:
    try:
        if contrast(theme.secondary_color, theme.background_color) >= MIN_LAND_CONTRAST:
            return theme.secondary_color
    except (ValueError, IndexError, AttributeError):
        pass
    return LAND_FALLBACK


def _colour(theme: Theme, kind: str) -> Optional[str]:
    return {
        "l": land_colour(theme),
        "r": theme.accent_color,
        "1": theme.text_color,
        "2": theme.warning_color,
        "3": theme.error_color,
    }.get(kind)


def map_text(theme: Theme, data: Dict[str, Any] | None, width: int, height: int, size: float,
             regions: bool = False) -> ft.Text:
    points = (data or {}).get("points") or []
    render = render_world_map(points, width, height, regions=list(STRATEGIC_REGIONS.values()) if regions else ())
    spans: List[ft.TextSpan] = []
    for index, (line, kinds) in enumerate(zip(render.lines, render.kinds)):
        for text, kind in kind_runs(line, kinds):
            colour = _colour(theme, kind)
            bold = kind in {"2", "3"}
            spans.append(ft.TextSpan(text, ft.TextStyle(color=colour, weight=ft.FontWeight.BOLD if bold else None)))
        if index < len(render.lines) - 1:
            spans.append(ft.TextSpan("\n"))
    return ft.Text(spans=spans, font_family=theme.font_family, size=size, no_wrap=True,
                   style=ft.TextStyle(height=1.0), data={"role": "world_map", "plotted": render.plotted})


def map_status_line(data: Dict[str, Any] | None, busy: bool = False) -> str:
    if busy:
        return "MAP: fetching GDELT events..."
    if not data:
        return "MAP: not loaded (REFRESH or Ctrl+M)"
    fetched = str(data.get("news_fetched_at") or "--")[:16].replace("T", " ")
    return (f"MAP: {data.get('feed_count', 0)} BELLATOR + {data.get('news_count', 0)} GDELT events "
            f"({data.get('news_status', 'unknown')}, {fetched} UTC)")


def build_mini_map(theme: Theme, data: Dict[str, Any] | None, busy: bool = False) -> ft.Control:
    width, height = MINI_SIZE
    return ft.Container(
        ft.Column(
            [
                map_text(theme, data, width, height, size=7),
                ft.Text(map_status_line(data, busy), color=theme.text_color, size=9, max_lines=2,
                        font_family=theme.font_family, text_align=ft.TextAlign.CENTER),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.top_center,
        data={"role": "world_mini_map"},
    )


def _event_rows(theme: Theme, data: Dict[str, Any] | None, limit: int = 12) -> List[ft.Control]:
    points = sorted((data or {}).get("points") or [], key=lambda point: (point.get("layer") == "feed",
                    float(point.get("severity") or 0)), reverse=True)
    rows = []
    for point in points[:limit]:
        layer = "BELLATOR" if point.get("layer") == "feed" else "GDELT"
        text = (f"{layer:<8} sev {float(point.get('severity') or 0):>4.1f}  {str(point.get('event_type') or ''):<14}"
                f" {str(point.get('place') or '')[:60]}")
        rows.append(ft.Text(text, color=theme.text_color, font_family=theme.font_family, size=10, no_wrap=True,
                            selectable=True, tooltip=str(point.get("url") or point.get("summary") or "")))
    if not rows:
        rows.append(ft.Text("No events with coordinates yet.", color=theme.text_color, size=10))
    return rows


def build_world_map_overlay(theme: Theme, data: Dict[str, Any] | None, *, busy: bool, page_width: float | None,
                            page_height: float | None = None, on_refresh=None, on_close=None) -> ft.Control:
    width, height = BIG_SIZE
    available = max(600.0, float(page_width or 1400) - 40)
    # Consolas characters are about 0.55 em wide; size the font so the map fills the overlay width,
    # and keep the whole map on screen below the title and above the footer (about 170 px).
    size = max(6.0, min(13.0, available / (width * 0.56)))
    if page_height:
        size = max(6.0, min(size, (float(page_height) - 170) / height))
    button_style = ft.ButtonStyle(color=theme.accent_color, shape=ft.RoundedRectangleBorder(radius=0))
    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text("BELLATOR WORLD MAP", color=theme.primary_color, weight=ft.FontWeight.BOLD, expand=True),
                    ft.TextButton("REFRESH", on_click=on_refresh, style=button_style, disabled=busy),
                    ft.TextButton("CLOSE", on_click=on_close, style=button_style),
                ]
            ),
            ft.Text(map_status_line(data, busy), color=theme.text_color, size=10, font_family=theme.font_family,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(map_text(theme, data, width, height, size=size, regions=True),
                         border=ft.border.all(1, land_colour(theme)), padding=4),
            ft.Text(LEGEND, color=theme.text_color, size=10, font_family=theme.font_family, text_align=ft.TextAlign.CENTER),
            ft.Text("GDELT events are machine-coded from news reports and appear on the map only; BELLATOR does not "
                    "vote on them.", color=theme.text_color, size=9, italic=True, text_align=ft.TextAlign.CENTER),
            ft.Divider(color=theme.secondary_color),
            # The list keeps its rows aligned with each other; the block as a whole is centred.
            ft.Column([ft.Text("STRONGEST EVENTS", color=theme.accent_color, weight=ft.FontWeight.BOLD, size=11),
                       *_event_rows(theme, data)], spacing=4),
        ],
        spacing=4,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        data={"role": "world_map_overlay"},
    )
