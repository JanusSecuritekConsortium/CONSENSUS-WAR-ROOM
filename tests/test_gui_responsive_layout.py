from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.header import GUI_HEADER_HEIGHT, theme_header_height
from ui.flet_app import (
    CENTER_COLUMN_FLEX,
    FOOTER_HEIGHT,
    LEFT_COLUMN_FLEX,
    RIGHT_COLUMN_FLEX,
    _apply_page_theme,
    build_gui_layout,
    create_gui_state,
)


class FakePage:
    title = ""
    bgcolor = ""
    theme = None
    scroll = "auto"
    padding = 10
    spacing = 10


def _noop(*_args, **_kwargs) -> None:
    return None


def _layout(theme_key: str = "EVA") -> ft.Control:
    state = create_gui_state(theme_key, RuntimeConfig(theme=theme_key, backend="mock"))
    return build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)


def test_body_has_responsive_left_center_right_regions() -> None:
    layout = _layout()
    body_row = layout.content.controls[1].content
    left, center, right = body_row.controls

    assert len(body_row.controls) == 3
    assert left.expand == LEFT_COLUMN_FLEX
    assert center.expand == CENTER_COLUMN_FLEX
    assert right.expand == RIGHT_COLUMN_FLEX


def test_fixed_header_footer_and_expanding_body() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    shell = layout.content
    header = shell.controls[0]
    body = shell.controls[1]
    footer = shell.controls[2]

    assert 120 <= GUI_HEADER_HEIGHT <= 200
    assert header.height == theme_header_height(state.theme)
    assert body.expand is True
    assert footer.height == FOOTER_HEIGHT
    assert 55 <= FOOTER_HEIGHT <= 70


def test_left_column_contains_readiness_section_below_monolith_cards() -> None:
    layout = _layout()
    left_column = layout.content.controls[1].content.controls[0].content
    readiness = left_column.controls[-1]
    readiness_title = readiness.content.controls[0].value

    assert readiness_title == "TRIBUNAL READINESS"
    assert readiness.expand is True


def test_no_page_level_scroll_by_default() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    page = FakePage()

    _apply_page_theme(page, state)

    assert page.scroll is None


if __name__ == "__main__":
    test_body_has_responsive_left_center_right_regions()
    test_fixed_header_footer_and_expanding_body()
    test_left_column_contains_readiness_section_below_monolith_cards()
    test_no_page_level_scroll_by_default()
    print("test_gui_responsive_layout PASS")
