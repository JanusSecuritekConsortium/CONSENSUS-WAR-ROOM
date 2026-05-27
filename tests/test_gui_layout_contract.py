from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.header import COMPACT_LOGO_MAX_LINES, GUI_HEADER_HEIGHT, compact_logo_text, logo_text_control_from_box
from ui.flet_app import _apply_page_theme, build_gui_layout, create_gui_state


class FakePage:
    title = ""
    bgcolor = ""
    theme = None
    scroll = "auto"
    padding = 10
    spacing = 10


def _noop(*_args, **_kwargs) -> None:
    return None


def _layout_for(theme_key: str = "EVA") -> ft.Control:
    state = create_gui_state(theme_key, RuntimeConfig(theme=theme_key, backend="mock"))
    return build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)


def test_header_has_bounded_height_and_compact_logo() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    header = layout.content.controls[0]
    logo_text = logo_text_control_from_box(header.content.controls[0]).value

    assert 120 <= GUI_HEADER_HEIGHT <= 180
    assert header.height == GUI_HEADER_HEIGHT
    assert logo_text == compact_logo_text(state.theme)
    assert logo_text != state.theme.logo.rstrip("\n")
    assert len(logo_text.splitlines()) <= COMPACT_LOGO_MAX_LINES
    telemetry_labels = [row.controls[0].value for row in header.content.controls[1].content.controls[1:7]]
    assert "ACTIVE MODE" in telemetry_labels
    assert "SESSION" in telemetry_labels


def test_main_body_expands_and_footer_is_fixed() -> None:
    layout = _layout_for()
    shell = layout.content
    body_container = shell.controls[1]
    footer = shell.controls[2]

    assert layout.expand is True
    assert shell.expand is True
    assert body_container.expand is True
    assert body_container.content.expand is True
    assert footer.height is not None


def test_log_panel_scrolls_internally() -> None:
    layout = _layout_for()
    body_row = layout.content.controls[1].content
    right_column = body_row.controls[2].content
    log_panel = right_column.controls[1]

    assert log_panel.expand is True
    assert log_panel.content.scroll == ft.ScrollMode.AUTO


def test_recent_decisions_have_verdict_colors() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    state.recent_decisions = [
        "APPROVED | eva | 111",
        "DENIED | eva | 222",
        "DEADLOCK | eva | 333",
    ]
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    body_row = layout.content.controls[1].content
    right_column = body_row.controls[2].content
    log_panel = right_column.controls[1]
    decision_rows = log_panel.content.controls[4]
    colors = [row.color for row in decision_rows.controls]

    assert colors == [state.theme.primary_color, state.theme.error_color, state.theme.warning_color]


def test_readiness_panel_includes_lifecycle() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    left_column = layout.content.controls[1].content.controls[0].content
    readiness = left_column.controls[-1]
    readiness_rows = readiness.content.controls[1]
    labels = [row.controls[1].value for row in readiness_rows.controls]

    assert "LIFECYCLE" in labels


def test_page_level_scroll_is_disabled_by_default() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    page = FakePage()

    _apply_page_theme(page, state)

    assert page.scroll is None
    assert page.padding == 0
    assert page.spacing == 0


if __name__ == "__main__":
    test_header_has_bounded_height_and_compact_logo()
    test_main_body_expands_and_footer_is_fixed()
    test_log_panel_scrolls_internally()
    test_recent_decisions_have_verdict_colors()
    test_readiness_panel_includes_lifecycle()
    test_page_level_scroll_is_disabled_by_default()
    print("test_gui_layout_contract PASS")
