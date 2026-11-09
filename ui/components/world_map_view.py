"""ASCII world map controls: the mini map in the BELLATOR panel and the full-screen map (Ctrl+M)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import flet as ft

from core.intelligence.strategic_regions import STRATEGIC_REGIONS
from core.intelligence.world_map import kind_runs, render_world_map
from core.models import Theme

MINI_SIZE = (60, 16)
BIG_SIZE = (150, 44)
LEGEND = "x/X BELLATOR feed event   + * # GDELT news: low / medium / high severity   +--+ strategic region"


def _colour(theme: Theme, kind: str) -> Optional[str]:
    return {
        "l": theme.secondary_color,
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
    return ft.Column(
        [
            map_text(theme, data, width, height, size=7),
            ft.Text(map_status_line(data, busy), color=theme.text_color, size=9, max_lines=2,
                    font_family=theme.font_family),
        ],
        spacing=2,
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
                            on_refresh=None, on_close=None) -> ft.Control:
    width, height = BIG_SIZE
    available = max(600.0, float(page_width or 1400) - 100)
    # Consolas characters are about 0.55 em wide; size the font so the map fills the overlay width.
    size = max(6.0, min(12.0, available / (width * 0.56)))
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
            ft.Text(map_status_line(data, busy), color=theme.text_color, size=10, font_family=theme.font_family),
            ft.Container(map_text(theme, data, width, height, size=size, regions=True),
                         border=ft.border.all(1, theme.secondary_color), padding=4),
            ft.Text(LEGEND, color=theme.text_color, size=10, font_family=theme.font_family),
            ft.Text("GDELT events are machine-coded from news reports and appear on the map only; BELLATOR does not "
                    "vote on them.", color=theme.text_color, size=9, italic=True),
            ft.Divider(color=theme.secondary_color),
            ft.Text("STRONGEST EVENTS", color=theme.accent_color, weight=ft.FontWeight.BOLD, size=11),
            *_event_rows(theme, data),
        ],
        spacing=4,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        data={"role": "world_map_overlay"},
    )
