from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import body_expand_contract, build_layout_for, header_logo_control_for, make_gui_state
from ui.components.header import LOGO_FONT_FAMILY, header_logo_text
from ui.layout_contract import CENTER_COLUMN_FLEX, LEFT_COLUMN_FLEX, RIGHT_COLUMN_FLEX
from ui.themes.catalog import get_gui_theme_options


def _header_logo_control(theme_key: str) -> ft.Text:
    return header_logo_control_for(theme_key)


def test_all_gui_themes_render_registered_logo_text() -> None:
    for theme in get_gui_theme_options():
        state = make_gui_state(theme.key)
        logo = _header_logo_control(theme.key)

        assert logo.value == header_logo_text(state.theme)
        assert logo._Control__attrs["nowrap"][0] is True
        assert logo.selectable is False
        assert logo.font_family == LOGO_FONT_FAMILY


def test_logo_header_keeps_body_layout_contract() -> None:
    layout = build_layout_for("arasaka")

    assert body_expand_contract(layout) == [LEFT_COLUMN_FLEX, CENTER_COLUMN_FLEX, RIGHT_COLUMN_FLEX]
    assert hasattr(layout, "diagnostics_drawer")
    assert hasattr(layout, "command_palette")


if __name__ == "__main__":
    test_all_gui_themes_render_registered_logo_text()
    test_logo_header_keeps_body_layout_contract()
    print("test_theme_logo_rendering PASS")
