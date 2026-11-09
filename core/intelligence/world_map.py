"""Draw an ASCII world map with event markers. Pure function: no network, no files, no GUI.

The map is equirectangular. Each cell gets a character and a kind code, so the GUI can colour it:
  " " sea, "l" land, "r" region outline, "1"/"2"/"3" low/medium/high severity marker.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.intelligence.world_land_mask import LAND_MASK

LAND_CHAR = "."
SEA_CHAR = " "
REGION_CHARS = {"corner": "+", "horizontal": "-", "vertical": "|"}
# GDELT news events and BELLATOR's own feed events use different marks.
MARKERS = {
    "news": {"1": "+", "2": "*", "3": "#"},
    "feed": {"1": "x", "2": "X", "3": "X"},
}
DEFAULT_LAT_TOP = 84.0
DEFAULT_LAT_BOTTOM = -58.0


@dataclass(frozen=True)
class MapRender:
    lines: List[str]
    kinds: List[str]
    plotted: int
    skipped: int


def severity_level(severity: Any) -> str:
    try:
        value = float(severity)
    except (TypeError, ValueError):
        return "1"
    if value >= 7.0:
        return "3"
    if value >= 5.0:
        return "2"
    return "1"


def land_fraction(lat_top: float, lat_bottom: float, lon_left: float, lon_right: float) -> float:
    """Share of 1 degree mask cells that are land inside a lat/lon box."""
    row_start = max(0, int(90.0 - lat_top))
    row_end = min(179, max(row_start, int(90.0 - lat_bottom - 1e-9)))
    col_start = max(0, int(lon_left + 180.0))
    col_end = min(359, max(col_start, int(lon_right + 180.0 - 1e-9)))
    land = total = 0
    for row in range(row_start, row_end + 1):
        line = LAND_MASK[row]
        for column in range(col_start, col_end + 1):
            total += 1
            land += line[column] == "#"
    return land / total if total else 0.0


def _cell(lat: float, lon: float, width: int, height: int, lat_top: float, lat_bottom: float) -> Optional[Tuple[int, int]]:
    if not (lat_bottom <= lat <= lat_top) or not (-180.0 <= lon <= 180.0):
        return None
    column = min(width - 1, int((lon + 180.0) / 360.0 * width))
    row = min(height - 1, int((lat_top - lat) / (lat_top - lat_bottom) * height))
    return row, column


def _float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def render_world_map(
    points: Iterable[Dict[str, Any]],
    width: int = 120,
    height: int = 36,
    *,
    regions: Sequence[Dict[str, Any]] = (),
    lat_top: float = DEFAULT_LAT_TOP,
    lat_bottom: float = DEFAULT_LAT_BOTTOM,
    land_threshold: float = 0.35,
) -> MapRender:
    """Render points (dicts with lat, lon, severity and an optional layer "news" or "feed")."""
    width = max(20, int(width))
    height = max(8, int(height))
    lon_step = 360.0 / width
    lat_step = (lat_top - lat_bottom) / height
    chars = [[SEA_CHAR] * width for _ in range(height)]
    kinds = [[" "] * width for _ in range(height)]
    for row in range(height):
        top = lat_top - row * lat_step
        for column in range(width):
            left = -180.0 + column * lon_step
            if land_fraction(top, top - lat_step, left, left + lon_step) >= land_threshold:
                chars[row][column] = LAND_CHAR
                kinds[row][column] = "l"

    for region in regions:
        _draw_region(chars, kinds, region.get("bbox") or {}, width, height, lat_top, lat_bottom)

    # Strongest event wins a cell; BELLATOR's own feed events win ties over news.
    best: Dict[Tuple[int, int], Tuple[str, int, str]] = {}
    plotted = skipped = 0
    for point in points:
        lat, lon = _float(point.get("lat")), _float(point.get("lon"))
        cell = _cell(lat, lon, width, height, lat_top, lat_bottom) if lat is not None and lon is not None else None
        if cell is None:
            skipped += 1
            continue
        plotted += 1
        level = severity_level(point.get("severity"))
        layer = "feed" if point.get("layer") == "feed" else "news"
        rank = int(level) * 2 + (layer == "feed")
        if cell not in best or rank > best[cell][1]:
            best[cell] = (level, rank, layer)
    for (row, column), (level, _rank, layer) in best.items():
        chars[row][column] = MARKERS[layer][level]
        kinds[row][column] = level

    return MapRender(["".join(line) for line in chars], ["".join(line) for line in kinds], plotted, skipped)


def _draw_region(chars, kinds, bbox: Dict[str, Any], width: int, height: int, lat_top: float, lat_bottom: float) -> None:
    try:
        north, south = float(bbox["lat_max"]), float(bbox["lat_min"])
        west, east = float(bbox["lon_min"]), float(bbox["lon_max"])
    except (KeyError, TypeError, ValueError):
        return
    top_left = _cell(min(north, lat_top), west, width, height, lat_top, lat_bottom)
    bottom_right = _cell(max(south, lat_bottom), east, width, height, lat_top, lat_bottom)
    if top_left is None or bottom_right is None:
        return
    (top, left), (bottom, right) = top_left, bottom_right
    for row in range(top, bottom + 1):
        for column in range(left, right + 1):
            on_row_edge = row in (top, bottom)
            on_column_edge = column in (left, right)
            if not (on_row_edge or on_column_edge):
                continue
            if on_row_edge and on_column_edge:
                char = REGION_CHARS["corner"]
            elif on_row_edge:
                char = REGION_CHARS["horizontal"]
            else:
                char = REGION_CHARS["vertical"]
            chars[row][column] = char
            kinds[row][column] = "r"


def kind_runs(line: str, kinds: str) -> List[Tuple[str, str]]:
    """Split a rendered line into (text, kind) runs so the GUI can colour each run once."""
    runs: List[Tuple[str, str]] = []
    for char, kind in zip(line, kinds):
        if runs and runs[-1][1] == kind:
            runs[-1] = (runs[-1][0] + char, kind)
        else:
            runs.append((char, kind))
    return runs
