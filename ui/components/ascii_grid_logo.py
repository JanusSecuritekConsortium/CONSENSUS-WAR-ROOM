from __future__ import annotations

from dataclasses import dataclass

import flet as ft
import flet.canvas as cv


CELL_WIDTH_UNITS = 0.62
CELL_HEIGHT_UNITS = 1.0
HORIZONTAL_FILL = 0.96
VERTICAL_FILL = 0.84
CELL_HORIZONTAL_FILL = 0.72
CELL_VERTICAL_FILL = 0.58


@dataclass(frozen=True)
class GridRun:
    row: int
    start_column: int
    length: int


@dataclass(frozen=True)
class GridCell:
    row: int
    column: int


@dataclass(frozen=True)
class AsciiGridLogoMetrics:
    source_rows: int
    source_max_columns: int
    visible_min_column: int
    visible_max_column: int
    visible_top_row: int
    visible_bottom_row: int
    visible_columns: int
    visible_rows: int
    run_count: int
    occupied_cell_count: int
    cell_aspect_ratio: float
    horizontal_fill: float
    vertical_fill: float
    cell_width: float
    cell_height: float
    scale: float
    origin_x: float
    origin_y: float
    visible_left: float
    visible_right: float
    visible_top: float
    visible_bottom: float
    width: float
    height: float

    @property
    def clearances(self) -> tuple[float, float, float, float]:
        return (
            self.visible_left,
            self.width - self.visible_right,
            self.visible_top,
            self.height - self.visible_bottom,
        )


def _occupied_runs(line: str, row: int) -> list[GridRun]:
    runs: list[GridRun] = []
    start: int | None = None
    for column, char in enumerate(line):
        if char != " " and start is None:
            start = column
        elif char == " " and start is not None:
            runs.append(GridRun(row=row, start_column=start, length=column - start))
            start = None
    if start is not None:
        runs.append(GridRun(row=row, start_column=start, length=len(line) - start))
    return runs


def ascii_grid_runs(source_text: str) -> list[GridRun]:
    runs: list[GridRun] = []
    for row, line in enumerate(source_text.splitlines()):
        runs.extend(_occupied_runs(line, row))
    return runs


def ascii_grid_cells(source_text: str) -> list[GridCell]:
    cells: list[GridCell] = []
    for row, line in enumerate(source_text.splitlines()):
        cells.extend(GridCell(row=row, column=column) for column, char in enumerate(line) if char != " ")
    return cells


def ascii_grid_metrics(
    source_text: str,
    *,
    width: float,
    height: float,
    margin: float = 8.0,
    cell_aspect_ratio: float = CELL_WIDTH_UNITS,
    horizontal_fill: float = HORIZONTAL_FILL,
    vertical_fill: float = VERTICAL_FILL,
    render_mode: str = "runs",
) -> AsciiGridLogoMetrics:
    lines = source_text.splitlines()
    source_rows = len(lines)
    source_max_columns = max((len(line) for line in lines), default=0)
    runs = ascii_grid_runs(source_text)
    if not runs:
        return AsciiGridLogoMetrics(
            source_rows=source_rows,
            source_max_columns=source_max_columns,
            visible_min_column=0,
            visible_max_column=0,
            visible_top_row=0,
            visible_bottom_row=0,
            visible_columns=0,
            visible_rows=0,
            run_count=0,
            occupied_cell_count=0,
            cell_aspect_ratio=cell_aspect_ratio,
            horizontal_fill=horizontal_fill,
            vertical_fill=vertical_fill,
            cell_width=0.0,
            cell_height=0.0,
            scale=0.0,
            origin_x=width / 2,
            origin_y=height / 2,
            visible_left=width / 2,
            visible_right=width / 2,
            visible_top=height / 2,
            visible_bottom=height / 2,
            width=width,
            height=height,
        )

    visible_min_column = min(run.start_column for run in runs)
    visible_max_column = max(run.start_column + run.length for run in runs)
    visible_top_row = min(run.row for run in runs)
    visible_bottom_row = max(run.row + 1 for run in runs)
    visible_columns = visible_max_column - visible_min_column
    visible_rows = visible_bottom_row - visible_top_row
    occupied_cell_count = sum(run.length for run in runs)

    usable_width = width - (margin * 2)
    usable_height = height - (margin * 2)
    visible_logical_width = visible_columns * cell_aspect_ratio
    visible_logical_height = visible_rows * CELL_HEIGHT_UNITS
    scale = min(usable_width / visible_logical_width, usable_height / visible_logical_height)
    cell_width = cell_aspect_ratio * scale
    cell_height = scale

    if render_mode == "cells":
        cells = ascii_grid_cells(source_text)
        uncentered_left = min(cell.column * cell_width for cell in cells)
        uncentered_right = max((cell.column + horizontal_fill) * cell_width for cell in cells)
        uncentered_top = min(cell.row * cell_height for cell in cells)
        uncentered_bottom = max((cell.row + vertical_fill) * cell_height for cell in cells)
    else:
        uncentered_left = min(run.start_column * cell_width for run in runs)
        uncentered_right = max((run.start_column + (run.length * horizontal_fill)) * cell_width for run in runs)
        uncentered_top = min(run.row * cell_height for run in runs)
        uncentered_bottom = max((run.row + vertical_fill) * cell_height for run in runs)
    drawn_width = uncentered_right - uncentered_left
    drawn_height = uncentered_bottom - uncentered_top
    origin_x = ((width - drawn_width) / 2) - uncentered_left
    origin_y = ((height - drawn_height) / 2) - uncentered_top

    return AsciiGridLogoMetrics(
        source_rows=source_rows,
        source_max_columns=source_max_columns,
        visible_min_column=visible_min_column,
        visible_max_column=visible_max_column,
        visible_top_row=visible_top_row,
        visible_bottom_row=visible_bottom_row,
        visible_columns=visible_columns,
        visible_rows=visible_rows,
        run_count=len(runs),
        occupied_cell_count=occupied_cell_count,
        cell_aspect_ratio=cell_aspect_ratio,
        horizontal_fill=horizontal_fill,
        vertical_fill=vertical_fill,
        cell_width=cell_width,
        cell_height=cell_height,
        scale=scale,
        origin_x=origin_x,
        origin_y=origin_y,
        visible_left=origin_x + uncentered_left,
        visible_right=origin_x + uncentered_right,
        visible_top=origin_y + uncentered_top,
        visible_bottom=origin_y + uncentered_bottom,
        width=width,
        height=height,
    )


def build_ascii_grid_logo(
    source_text: str,
    width: float,
    height: float,
    foreground: str,
    margin: float = 8.0,
    cell_aspect_ratio: float = CELL_WIDTH_UNITS,
    render_mode: str = "cells",
) -> ft.Control:
    horizontal_fill = CELL_HORIZONTAL_FILL if render_mode == "cells" else HORIZONTAL_FILL
    vertical_fill = CELL_VERTICAL_FILL if render_mode == "cells" else VERTICAL_FILL
    metrics = ascii_grid_metrics(
        source_text,
        width=width,
        height=height,
        margin=margin,
        cell_aspect_ratio=cell_aspect_ratio,
        horizontal_fill=horizontal_fill,
        vertical_fill=vertical_fill,
        render_mode=render_mode,
    )
    paint = ft.Paint(color=foreground, style=ft.PaintingStyle.FILL, anti_alias=False)
    if render_mode == "cells":
        shapes = [
            cv.Rect(
                x=metrics.origin_x + (cell.column * metrics.cell_width),
                y=metrics.origin_y + (cell.row * metrics.cell_height),
                width=metrics.cell_width * metrics.horizontal_fill,
                height=metrics.cell_height * metrics.vertical_fill,
                paint=paint,
                data={"role": "ascii_grid_cell", "row": cell.row, "column": cell.column},
            )
            for cell in ascii_grid_cells(source_text)
        ]
    else:
        shapes = [
            cv.Rect(
                x=metrics.origin_x + (run.start_column * metrics.cell_width),
                y=metrics.origin_y + (run.row * metrics.cell_height),
                width=run.length * metrics.cell_width * metrics.horizontal_fill,
                height=metrics.cell_height * metrics.vertical_fill,
                paint=paint,
                data={"role": "ascii_grid_run", "row": run.row, "start_column": run.start_column, "length": run.length},
            )
            for run in ascii_grid_runs(source_text)
        ]
    canvas = cv.Canvas(
        shapes=shapes,
        width=width,
        height=height,
        data={
            "role": "ascii_grid_canvas",
            "renderer_mode": "ascii_grid_vector",
            "run_count": metrics.run_count,
            "occupied_cell_count": metrics.occupied_cell_count,
            "source_text": source_text,
        },
    )
    return ft.Container(
        content=canvas,
        width=width,
        height=height,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={
            "role": "ascii_grid_logo",
            "renderer_mode": "ascii_grid_vector",
            "uses_canvas": True,
            "uses_text_control": False,
            "source_text": source_text,
            "source_rows": metrics.source_rows,
            "source_max_columns": metrics.source_max_columns,
            "visible_columns": metrics.visible_columns,
            "visible_rows": metrics.visible_rows,
            "run_count": metrics.run_count,
            "occupied_cell_count": metrics.occupied_cell_count,
            "render_mode": render_mode,
            "cell_aspect_ratio": metrics.cell_aspect_ratio,
            "horizontal_fill": metrics.horizontal_fill,
            "vertical_fill": metrics.vertical_fill,
            "cell_width": metrics.cell_width,
            "cell_height": metrics.cell_height,
            "visible_bounds": (
                metrics.visible_left,
                metrics.visible_right,
                metrics.visible_top,
                metrics.visible_bottom,
            ),
            "clearances": metrics.clearances,
        },
    )


__all__ = [
    "AsciiGridLogoMetrics",
    "CELL_HEIGHT_UNITS",
    "CELL_HORIZONTAL_FILL",
    "CELL_VERTICAL_FILL",
    "CELL_WIDTH_UNITS",
    "GridCell",
    "GridRun",
    "HORIZONTAL_FILL",
    "VERTICAL_FILL",
    "ascii_grid_cells",
    "ascii_grid_metrics",
    "ascii_grid_runs",
    "build_ascii_grid_logo",
]
