from __future__ import annotations

import hashlib
from dataclasses import dataclass

import flet as ft

from config.version import SYSTEM_VERSION
from core.logging import log_event
from core.models import Theme
from ui.assets.registry import HeaderLogoLayout, HeaderLogoProfile, THEME_GRAPHIC_ASSETS, get_theme_graphic_asset
from ui.components.ascii_grid_logo import CELL_HORIZONTAL_FILL, CELL_VERTICAL_FILL, ascii_grid_metrics, build_ascii_grid_logo
from ui.components.safe_text import safe_ellipsis
from ui.components.telemetry_widgets import build_themed_telemetry

GUI_HEADER_HEIGHT = 190
COMPACT_LOGO_MAX_LINES = 12
GUI_LOGO_BOX_HEIGHT = GUI_HEADER_HEIGHT - 28
GUI_LOGO_BOX_MAX_WIDTH = 1120
HEADER_LOGO_FLEX = 23
HEADER_STATUS_FLEX = 77
HEADER_LOGO_VIEWPORT_WIDTH_ESTIMATE = 420
THEME_HEADER_SPLITS = {
    "default": (HEADER_LOGO_FLEX, HEADER_STATUS_FLEX),
    "arasaka": (34, 66),
    "janus": (18, 82),
    "helldivers": (20, 80),
}
THEME_LOGO_LAYOUTS = {
    "default": {"mode": "percentage", "split": THEME_HEADER_SPLITS["default"]},
    "arasaka": {"mode": "percentage", "split": THEME_HEADER_SPLITS["arasaka"]},
    "janus": {"mode": "percentage", "split": THEME_HEADER_SPLITS["janus"]},
    "helldivers": {"mode": "percentage", "split": THEME_HEADER_SPLITS["helldivers"]},
    "eva": {"mode": "supersampled_rect"},
    "nerv": {"mode": "supersampled_rect"},
    "wh40k": {"mode": "supersampled_rect"},
    "military": {"mode": "supersampled_banner"},
}
HEADER_STATUS_METADATA_FLEX = 68
HEADER_TELEMETRY_FLEX = 32
LOGO_FONT_FAMILY = "Consolas"
LOGO_CHAR_WIDTH_FACTOR = 0.62
SUPERSAMPLED_LOGO_MARGIN = 6
SUPERSAMPLED_BANNER_MARGIN = 20
MILITARY_HISTORICAL_RENDERER_COMMIT = "f7248fc"
MILITARY_FONT_REGISTRATION_PATH = None
LOGO_FONT_SIZE = 12
GUI_COMPACT_LOGO_FILES = {key: asset.logo_path for key, asset in THEME_GRAPHIC_ASSETS.items()}
HEADER_TELEMETRY_HEIGHT = 132
HEADER_STATUS_TEXT_SIZES = {
    "default": {"title": 17, "row": 12, "ambient": 11},
}
_LOGO_SCALE_DIAGNOSTIC_EMITTED: set[str] = set()
_SUPERSAMPLED_LOGO_DIAGNOSTIC_EMITTED: set[str] = set()


@dataclass(frozen=True)
class SupersampledLogoMetrics:
    cell_width: float
    cell_height: float
    source_line_count: int
    source_max_columns: int
    visible_min_column: int
    visible_max_column: int
    visible_top_line: int
    visible_bottom_line: int
    visible_columns: int
    visible_rows: int
    base_font_size: int
    char_width: float
    line_height: float
    natural_width: float
    natural_height: float
    natural_visible_width: float
    natural_visible_height: float
    fit_scale: float
    transformed_width: float
    transformed_height: float
    canvas_left: float
    canvas_top: float
    visible_left: float
    visible_right: float
    visible_top: float
    visible_bottom: float

    @property
    def clearances(self) -> tuple[float, float, float, float]:
        return (
            self.visible_left,
            self.cell_width - self.visible_right,
            self.visible_top,
            self.cell_height - self.visible_bottom,
        )


def _read_logo_text_preserved(path) -> str:
    return path.read_bytes().decode("utf-8")


def _logo_width(logo: str) -> int:
    longest = max((len(line) for line in logo.splitlines()), default=64)
    return max(360, min(GUI_LOGO_BOX_MAX_WIDTH, int(longest * 7.5) + 32))


def _logo_box_width(logo: str, layout: HeaderLogoLayout, *, cap_to_viewport: bool = True) -> int:
    if layout.logo_box_width is not None:
        if cap_to_viewport:
            return min(layout.logo_box_width, HEADER_LOGO_VIEWPORT_WIDTH_ESTIMATE)
        return layout.logo_box_width
    calculated = _logo_width(logo)
    if layout.logo_box_max_width is not None:
        capped = min(layout.logo_box_max_width, calculated)
        return min(capped, HEADER_LOGO_VIEWPORT_WIDTH_ESTIMATE) if cap_to_viewport else capped
    return min(calculated, HEADER_LOGO_VIEWPORT_WIDTH_ESTIMATE) if cap_to_viewport else calculated


def _logo_box_height(layout: HeaderLogoLayout) -> int:
    return GUI_LOGO_BOX_HEIGHT


def theme_header_height(theme: Theme) -> int:
    return GUI_HEADER_HEIGHT


def header_logo_layout(theme: Theme) -> HeaderLogoLayout:
    try:
        return get_theme_graphic_asset(theme.key).header_layout
    except KeyError:
        return HeaderLogoLayout(logo_font_size=LOGO_FONT_SIZE)


def theme_header_split(theme: Theme) -> tuple[int, int]:
    return THEME_HEADER_SPLITS.get(theme.key, THEME_HEADER_SPLITS["default"])


def theme_logo_layout_mode(theme: Theme) -> dict[str, object]:
    return THEME_LOGO_LAYOUTS.get(theme.key, THEME_LOGO_LAYOUTS["default"])


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


def _logo_scale_transform(layout: HeaderLogoLayout) -> ft.Scale | None:
    if layout.logo_visual_scale == 1:
        return None
    return ft.Scale(scale=layout.logo_visual_scale, alignment=ft.alignment.center)


def _visible_logo_columns_and_rows(logo: str) -> tuple[int, int]:
    visible_lines = [line for line in logo.splitlines() if line.strip()]
    min_column = min((len(line) - len(line.lstrip(" ")) for line in visible_lines), default=0)
    max_column = max((len(line.rstrip(" ")) for line in visible_lines), default=0)
    return max_column - min_column, len(visible_lines)


def _visible_logo_box(logo: str) -> tuple[int, int, int, int]:
    lines = logo.splitlines()
    visible_lines = [(index, line) for index, line in enumerate(lines) if line.strip()]
    if not visible_lines:
        return 0, 0, 0, 0
    min_column = min(len(line) - len(line.lstrip(" ")) for _index, line in visible_lines)
    max_column = max(len(line.rstrip(" ")) for _index, line in visible_lines)
    top_line = visible_lines[0][0]
    bottom_line = visible_lines[-1][0] + 1
    return min_column, max_column, top_line, bottom_line


def supersampled_logo_metrics(
    logo: str,
    *,
    base_font_size: int = 10,
    cell_size: int = GUI_LOGO_BOX_HEIGHT,
    cell_width: int | None = None,
    cell_height: int | None = None,
    margin: int = SUPERSAMPLED_LOGO_MARGIN,
    line_height_factor: float = 1.0,
) -> SupersampledLogoMetrics:
    if base_font_size != int(base_font_size) or base_font_size < 8:
        raise ValueError(f"Supersampled ASCII logos require an integer base font size >= 8, got {base_font_size!r}")
    lines = logo.splitlines()
    source_line_count = len(lines)
    source_max_columns = max((len(line) for line in lines), default=0)
    min_column, max_column, top_line, bottom_line = _visible_logo_box(logo)
    visible_columns = max_column - min_column
    visible_rows = bottom_line - top_line
    resolved_width = float(cell_width or cell_size)
    resolved_height = float(cell_height or cell_size)
    char_width = base_font_size * LOGO_CHAR_WIDTH_FACTOR
    line_height = float(base_font_size) * float(line_height_factor)
    natural_width = source_max_columns * char_width
    natural_height = source_line_count * line_height
    natural_visible_width = visible_columns * char_width
    natural_visible_height = visible_rows * line_height
    usable_width = resolved_width - (margin * 2)
    usable_height = resolved_height - (margin * 2)
    fit_scale = min(usable_width / natural_visible_width, usable_height / natural_visible_height)
    transformed_width = natural_visible_width * fit_scale
    transformed_height = natural_visible_height * fit_scale
    visible_left = (resolved_width - transformed_width) / 2
    visible_top = (resolved_height - transformed_height) / 2
    canvas_left = visible_left - (min_column * char_width * fit_scale)
    canvas_top = visible_top - (top_line * line_height * fit_scale)
    return SupersampledLogoMetrics(
        source_line_count=source_line_count,
        cell_width=resolved_width,
        cell_height=resolved_height,
        source_max_columns=source_max_columns,
        visible_min_column=min_column,
        visible_max_column=max_column,
        visible_top_line=top_line,
        visible_bottom_line=bottom_line,
        visible_columns=visible_columns,
        visible_rows=visible_rows,
        base_font_size=int(base_font_size),
        char_width=char_width,
        line_height=line_height,
        natural_width=natural_width,
        natural_height=natural_height,
        natural_visible_width=natural_visible_width,
        natural_visible_height=natural_visible_height,
        fit_scale=fit_scale,
        transformed_width=transformed_width,
        transformed_height=transformed_height,
        canvas_left=canvas_left,
        canvas_top=canvas_top,
        visible_left=visible_left,
        visible_right=visible_left + transformed_width,
        visible_top=visible_top,
        visible_bottom=visible_top + transformed_height,
    )


def estimate_logo_visible_bounds(logo: str, layout: HeaderLogoLayout) -> tuple[float, float]:
    visible_width, visible_height = _visible_logo_columns_and_rows(logo)
    return visible_width * layout.logo_font_size * LOGO_CHAR_WIDTH_FACTOR, visible_height * layout.logo_font_size


def estimate_logo_transformed_bounds(logo: str, layout: HeaderLogoLayout) -> tuple[float, float]:
    width, height = estimate_logo_visible_bounds(logo, layout)
    return width * layout.logo_visual_scale, height * layout.logo_visual_scale


def logo_square_cell_clearances(
    logo: str,
    layout: HeaderLogoLayout,
    *,
    cell_size: int = GUI_LOGO_BOX_HEIGHT,
) -> tuple[float, float, float, float]:
    width, height = estimate_logo_transformed_bounds(logo, layout)
    horizontal = (cell_size - width) / 2
    vertical = (cell_size - height) / 2
    return horizontal, horizontal, vertical, vertical


def _supersampled_margin_for_mode(mode: str) -> int:
    return SUPERSAMPLED_BANNER_MARGIN if mode == "supersampled_banner" else SUPERSAMPLED_LOGO_MARGIN


def _supersampled_cell_width(mode: str, layout: HeaderLogoLayout) -> int:
    if mode in {"supersampled_rect", "supersampled_banner"}:
        return int(layout.logo_box_width or GUI_LOGO_BOX_HEIGHT)
    return GUI_LOGO_BOX_HEIGHT


def _supersampled_cell_height(mode: str, layout: HeaderLogoLayout) -> int:
    return int(layout.logo_box_height or GUI_LOGO_BOX_HEIGHT)


def _offset_supersampled_clearances(metrics: SupersampledLogoMetrics, layout: HeaderLogoLayout) -> tuple[float, float, float, float]:
    left = metrics.visible_left + layout.logo_offset_x
    right = metrics.cell_width - (metrics.visible_right + layout.logo_offset_x)
    top = metrics.visible_top + layout.logo_offset_y
    bottom = metrics.cell_height - (metrics.visible_bottom + layout.logo_offset_y)
    return left, right, top, bottom


def _log_logo_scale_diagnostic(theme: Theme, logo: str, layout: HeaderLogoLayout, cell_size: int) -> None:
    if layout.logo_visual_scale == 1 or theme.key in _LOGO_SCALE_DIAGNOSTIC_EMITTED:
        return
    pre_width, pre_height = estimate_logo_visible_bounds(logo, layout)
    transformed_width, transformed_height = estimate_logo_transformed_bounds(logo, layout)
    left, right, top, bottom = logo_square_cell_clearances(logo, layout, cell_size=cell_size)
    log_event(
        "header_logo_scale_resolved",
        {
            "theme": theme.key,
            "font_size": layout.logo_font_size,
            "visual_scale": layout.logo_visual_scale,
            "square_cell_width": cell_size,
            "square_cell_height": cell_size,
            "estimated_pre_transform_bounds": {"width": round(pre_width, 3), "height": round(pre_height, 3)},
            "transformed_bounds": {"width": round(transformed_width, 3), "height": round(transformed_height, 3)},
            "clearances": {
                "left": round(left, 3),
                "right": round(right, 3),
                "top": round(top, 3),
                "bottom": round(bottom, 3),
            },
        },
    )
    _LOGO_SCALE_DIAGNOSTIC_EMITTED.add(theme.key)


def _log_supersampled_logo_diagnostic(theme: Theme, logo: str, metrics: SupersampledLogoMetrics) -> None:
    if theme.key in _SUPERSAMPLED_LOGO_DIAGNOSTIC_EMITTED:
        return
    try:
        asset = get_theme_graphic_asset(theme.key)
        asset_path = str(asset.logo_path)
        asset_hash = hashlib.sha256(asset.logo_path.read_bytes()).hexdigest()
    except KeyError:
        asset_path = "<theme-logo>"
        asset_hash = hashlib.sha256(logo.encode("utf-8")).hexdigest()
    left, right, top, bottom = metrics.clearances
    log_event(
        "header_supersampled_logo_resolved",
        {
            "theme": theme.key,
            "asset_path": asset_path,
            "asset_sha256": asset_hash,
            "renderer_mode": theme_logo_layout_mode(theme)["mode"],
            "base_font_size": metrics.base_font_size,
            "line_count": metrics.source_line_count,
            "maximum_columns": metrics.source_max_columns,
            "natural_visible_width": round(metrics.natural_visible_width, 3),
            "natural_visible_height": round(metrics.natural_visible_height, 3),
            "fit_scale": round(metrics.fit_scale, 6),
            "transformed_width": round(metrics.transformed_width, 3),
            "transformed_height": round(metrics.transformed_height, 3),
            "clearances": {
                "left": round(left, 3),
                "right": round(right, 3),
                "top": round(top, 3),
                "bottom": round(bottom, 3),
            },
        },
    )
    _SUPERSAMPLED_LOGO_DIAGNOSTIC_EMITTED.add(theme.key)


class SupersampledAsciiLogo(ft.Stack):
    def __init__(self, logo: str, theme: Theme, layout: HeaderLogoLayout) -> None:
        mode = theme_logo_layout_mode(theme)["mode"]
        cell_width = _supersampled_cell_width(mode, layout)
        cell_height = _supersampled_cell_height(mode, layout)
        margin = _supersampled_margin_for_mode(mode)
        metrics = supersampled_logo_metrics(
            logo,
            base_font_size=int(layout.logo_font_size),
            cell_width=cell_width,
            cell_height=cell_height,
            margin=margin,
            line_height_factor=layout.logo_line_height,
        )
        final_clearances = _offset_supersampled_clearances(metrics, layout)
        _log_supersampled_logo_diagnostic(theme, logo, metrics)
        text = ft.Text(
            logo,
            font_family=LOGO_FONT_FAMILY,
            color=theme.primary_color,
            selectable=False,
            no_wrap=True,
            overflow=ft.TextOverflow.VISIBLE,
            style=ft.TextStyle(
                font_family=LOGO_FONT_FAMILY,
                size=metrics.base_font_size,
                weight=ft.FontWeight.NORMAL,
                height=layout.logo_line_height,
                letter_spacing=0,
                word_spacing=0,
                overflow=ft.TextOverflow.VISIBLE,
            ),
            size=metrics.base_font_size,
            weight=ft.FontWeight.NORMAL,
            data={
                "role": "theme_logo_text",
                "layout_mode": theme_logo_layout_mode(theme)["mode"],
                "base_font_size": metrics.base_font_size,
                "line_height": layout.logo_line_height,
                "fit_scale": metrics.fit_scale,
            },
        )
        natural_text_canvas = ft.Container(
            content=text,
            width=metrics.natural_width,
            height=metrics.natural_height,
            left=metrics.canvas_left + layout.logo_offset_x,
            top=metrics.canvas_top + layout.logo_offset_y,
            scale=ft.Scale(scale=metrics.fit_scale, alignment=ft.alignment.top_left),
            clip_behavior=ft.ClipBehavior.NONE,
            data={
                "role": "supersampled_ascii_logo_canvas",
                "base_font_size": metrics.base_font_size,
                "fit_scale": metrics.fit_scale,
                "natural_width": metrics.natural_width,
                "natural_height": metrics.natural_height,
                "transformed_width": metrics.transformed_width,
                "transformed_height": metrics.transformed_height,
                "clearances": final_clearances,
                "optical_offset_x": layout.logo_offset_x,
                "optical_offset_y": layout.logo_offset_y,
                "uniform_scale": True,
            },
        )
        super().__init__(
            controls=[natural_text_canvas],
            width=cell_width,
            height=cell_height,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            data={
                "role": "supersampled_ascii_logo_viewport",
                "layout_mode": mode,
                "width": cell_width,
                "height": cell_height,
                "fit_scale": metrics.fit_scale,
                "base_font_size": metrics.base_font_size,
            },
        )


def _logo_source_text(theme: Theme) -> str:
    try:
        asset = get_theme_graphic_asset(theme.key)
    except KeyError:
        return theme.logo
    return _read_logo_text_preserved(asset.logo_path)


def _build_logo_text(logo: str, theme: Theme) -> ft.Text:
    layout = header_logo_layout(theme)
    font_size = layout.logo_font_size
    text_overflow = None if theme.key == "military" else ft.TextOverflow.VISIBLE
    return ft.Text(
        logo,
        font_family=LOGO_FONT_FAMILY,
        color=theme.primary_color,
        selectable=False,
        no_wrap=True,
        overflow=text_overflow,
        style=ft.TextStyle(
            font_family=LOGO_FONT_FAMILY,
            size=font_size,
            height=1.0,
            letter_spacing=0,
            word_spacing=0,
            overflow=text_overflow,
        ),
        size=font_size,
        data={"role": "theme_logo_text", "layout_mode": theme_logo_layout_mode(theme)["mode"]},
    )


def system_status_label_color(theme: Theme) -> str:
    if theme.key == "arasaka":
        return theme.secondary_text or "#ff8a8f"
    return theme.secondary_color


def _build_scrollable_logo_content(logo: str, theme: Theme) -> ft.Column:
    layout = header_logo_layout(theme)
    if theme_logo_layout_mode(theme)["mode"] == "ascii_grid_vector":
        return ft.Column(
            [
                build_ascii_grid_logo(
                    logo,
                    width=float(layout.logo_box_width or GUI_LOGO_BOX_HEIGHT),
                    height=float(layout.logo_box_height or GUI_LOGO_BOX_HEIGHT),
                    foreground=theme.primary_color,
                    margin=8.0,
                )
            ],
            spacing=0,
            tight=True,
            scroll=None,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    if theme_logo_layout_mode(theme)["mode"] in {"supersampled_square", "supersampled_rect", "supersampled_banner"}:
        return ft.Column(
            [SupersampledAsciiLogo(logo, theme, layout)],
            spacing=0,
            tight=True,
            scroll=None,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
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
                scale=_logo_scale_transform(layout),
                margin=ft.margin.only(left=layout.logo_offset_x, top=layout.logo_offset_y),
                data={
                    "role": "theme_logo_scaled_content",
                    "visual_scale": layout.logo_visual_scale,
                    "scale_alignment": "center",
                    "uniform_scale": True,
                },
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
    return _logo_source_text(theme)


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
        return _read_logo_text_preserved(dedicated)
    lines = theme.logo.rstrip("\n").splitlines()
    first_visible = next((index for index, line in enumerate(lines) if line.strip()), 0)
    return "\n".join(lines[first_visible : first_visible + max_lines])


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
    status_sizes = _header_status_sizes(theme.key)
    logo_layout = header_logo_layout(theme)
    logo_profile = header_logo_profile(theme)
    logo_mode = theme_logo_layout_mode(theme)
    logo_flex, status_flex = tuple(logo_mode.get("split", THEME_HEADER_SPLITS["default"]))
    header_height = theme_header_height(theme)
    logo_box_height = _logo_box_height(logo_layout)
    logo_cell_size = logo_box_height
    logo_container_kwargs: dict[str, object]
    status_container_kwargs: dict[str, object]
    if logo_mode["mode"] in {"square", "supersampled_square", "supersampled_rect", "supersampled_banner", "ascii_grid_vector"}:
        logo_width = _logo_box_width(logo, logo_layout, cap_to_viewport=False) if logo_mode["mode"] in {"supersampled_rect", "supersampled_banner"} else logo_cell_size
        if logo_mode["mode"] == "ascii_grid_vector":
            logo_width = _logo_box_width(logo, logo_layout, cap_to_viewport=False)
        logo_height = int(logo_layout.logo_box_height or logo_cell_size) if logo_mode["mode"] in {"supersampled_rect", "supersampled_banner"} else logo_cell_size
        if logo_mode["mode"] == "ascii_grid_vector":
            logo_height = int(logo_layout.logo_box_height or logo_cell_size)
        logo_container_kwargs = {"width": logo_width, "height": logo_height}
        status_container_kwargs = {"expand": True}
    elif logo_mode["mode"] == "historical":
        logo_container_kwargs = {
            "width": _logo_box_width(logo, logo_layout, cap_to_viewport=False),
            "height": logo_box_height,
        }
        status_container_kwargs = {"expand": True}
    else:
        logo_container_kwargs = {"expand": logo_flex, "height": logo_box_height}
        status_container_kwargs = {"expand": status_flex}
    status_panel_height = header_height - 16
    telemetry_panel_height = min(HEADER_TELEMETRY_HEIGHT, max(100, status_panel_height - 42))
    if logo_mode["mode"] not in {"supersampled_square", "supersampled_rect", "supersampled_banner", "ascii_grid_vector"}:
        _log_logo_scale_diagnostic(theme, logo, logo_layout, logo_cell_size)
    logo_padding = (
        ft.padding.all(0)
        if logo_mode["mode"] in {"supersampled_square", "supersampled_rect", "supersampled_banner", "ascii_grid_vector"}
        else ft.padding.only(
            left=logo_layout.logo_side_padding,
            right=logo_layout.logo_side_padding,
            top=max(logo_layout.logo_top_padding, logo_profile.padding_top),
            bottom=max(logo_layout.logo_bottom_padding, logo_profile.padding_bottom),
        )
    )
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=_build_scrollable_logo_content(logo, theme),
                    **logo_container_kwargs,
                    padding=logo_padding,
                    alignment=_alignment(logo_layout),
                    border=ft.border.all(1, theme.secondary_color),
                    bgcolor=theme.background_color,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    data={
                        "role": "header_logo_viewport",
                        "layout_mode": logo_mode["mode"],
                        "square": logo_mode["mode"] in {"square", "supersampled_square"},
                    },
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
                                        expand=HEADER_STATUS_METADATA_FLEX,
                                    ),
                                    ft.Container(
                                        content=build_themed_telemetry(theme.key, telemetry, None, theme),
                                        expand=HEADER_TELEMETRY_FLEX,
                                        height=telemetry_panel_height,
                                        padding=ft.padding.only(left=10),
                                        border=ft.border.only(left=ft.BorderSide(1, theme.secondary_color)),
                                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                        data={
                                            "role": "header_telemetry_panel",
                                            "summary_lines": 5,
                                            "graph_lines": 1,
                                            "bounded": True,
                                            "themed_visual": True,
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
                    **status_container_kwargs,
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


def logo_runtime_diagnostics(theme: Theme | str, *, header_width: int = 1920) -> dict[str, object]:
    if isinstance(theme, str):
        from ui.themes.catalog import THEMES

        theme = THEMES[theme]
    logo = header_logo_text(theme)
    layout = header_logo_layout(theme)
    mode = theme_logo_layout_mode(theme)["mode"]
    inner_width = header_width - 16 - 12
    if mode in {"supersampled_rect", "supersampled_banner"}:
        region_width = float(layout.logo_box_width or GUI_LOGO_BOX_HEIGHT)
        region_height = float(layout.logo_box_height or GUI_LOGO_BOX_HEIGHT)
        metrics = supersampled_logo_metrics(
            logo,
            base_font_size=int(layout.logo_font_size),
            cell_width=int(region_width),
            cell_height=int(region_height),
            margin=_supersampled_margin_for_mode(mode),
            line_height_factor=layout.logo_line_height,
        )
        art_width = metrics.transformed_width
        art_height = metrics.transformed_height
        clearances = _offset_supersampled_clearances(metrics, layout)
    elif mode == "ascii_grid_vector":
        region_width = float(layout.logo_box_width or GUI_LOGO_BOX_HEIGHT)
        region_height = float(layout.logo_box_height or GUI_LOGO_BOX_HEIGHT)
        metrics = ascii_grid_metrics(
            logo,
            width=region_width,
            height=region_height,
            margin=8.0,
            horizontal_fill=CELL_HORIZONTAL_FILL,
            vertical_fill=CELL_VERTICAL_FILL,
            render_mode="cells",
        )
        art_width = metrics.visible_right - metrics.visible_left
        art_height = metrics.visible_bottom - metrics.visible_top
        clearances = metrics.clearances
    elif mode == "supersampled_square":
        region_width = float(GUI_LOGO_BOX_HEIGHT)
        region_height = float(GUI_LOGO_BOX_HEIGHT)
        metrics = supersampled_logo_metrics(
            logo,
            base_font_size=int(layout.logo_font_size),
            line_height_factor=layout.logo_line_height,
        )
        art_width = metrics.transformed_width
        art_height = metrics.transformed_height
        clearances = metrics.clearances
    elif mode == "historical":
        region_width = float(_logo_box_width(logo, layout, cap_to_viewport=False))
        region_height = float(_logo_box_height(layout))
        visible_width, visible_height = estimate_logo_transformed_bounds(logo, layout)
        art_width = visible_width
        art_height = visible_height
        clearances = (
            (region_width - art_width) / 2,
            (region_width - art_width) / 2,
            (region_height - art_height) / 2,
            (region_height - art_height) / 2,
        )
    else:
        split = tuple(theme_logo_layout_mode(theme).get("split", THEME_HEADER_SPLITS["default"]))
        region_width = inner_width * (float(split[0]) / float(split[0] + split[1]))
        region_height = float(_logo_box_height(layout))
        visible_width, visible_height = estimate_logo_transformed_bounds(logo, layout)
        art_width = visible_width
        art_height = visible_height
        clearances = (
            (region_width - art_width) / 2,
            (region_width - art_width) / 2,
            (region_height - art_height) / 2,
            (region_height - art_height) / 2,
        )
    return {
        "theme": theme.key,
        "renderer_mode": mode,
        "logo_region_width": round(region_width, 3),
        "logo_region_height": round(region_height, 3),
        "visible_artwork_width": round(art_width, 3),
        "visible_artwork_height": round(art_height, 3),
        "clearances": tuple(round(value, 3) for value in clearances),
        "optical_offset_x": layout.logo_offset_x if theme.key == "wh40k" else 0,
    }


__all__ = [
    "GUI_COMPACT_LOGO_FILES",
    "GUI_HEADER_HEIGHT",
    "GUI_LOGO_BOX_HEIGHT",
    "GUI_LOGO_BOX_MAX_WIDTH",
    "HEADER_LOGO_FLEX",
    "HEADER_STATUS_FLEX",
    "THEME_HEADER_SPLITS",
    "THEME_LOGO_LAYOUTS",
    "HEADER_STATUS_METADATA_FLEX",
    "HEADER_TELEMETRY_FLEX",
    "LOGO_FONT_FAMILY",
    "LOGO_FONT_SIZE",
    "HEADER_LOGO_VIEWPORT_WIDTH_ESTIMATE",
    "MILITARY_HISTORICAL_RENDERER_COMMIT",
    "MILITARY_FONT_REGISTRATION_PATH",
    "COMPACT_LOGO_MAX_LINES",
    "HEADER_TELEMETRY_HEIGHT",
    "LOGO_CHAR_WIDTH_FACTOR",
    "SUPERSAMPLED_LOGO_MARGIN",
    "SUPERSAMPLED_BANNER_MARGIN",
    "SupersampledAsciiLogo",
    "SupersampledLogoMetrics",
    "ascii_grid_metrics",
    "build_header",
    "compact_logo_text",
    "header_logo_profile",
    "header_logo_text",
    "header_logo_layout",
    "estimate_logo_visible_bounds",
    "estimate_logo_transformed_bounds",
    "logo_square_cell_clearances",
    "supersampled_logo_metrics",
    "theme_header_split",
    "theme_logo_layout_mode",
    "theme_header_height",
    "has_dedicated_gui_compact_logo",
    "logo_text_control_from_box",
    "logo_runtime_diagnostics",
    "system_status_label_color",
]
