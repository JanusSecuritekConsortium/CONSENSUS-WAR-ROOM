from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.header import LOGO_FONT_FAMILY, header_logo_text, logo_text_control_from_box
from ui.flet_app import build_gui_layout, create_gui_state
from ui.layout_contract import CENTER_COLUMN_FLEX, LEFT_COLUMN_FLEX, RIGHT_COLUMN_FLEX
from ui.themes.catalog import get_gui_theme_options
from ui.components.header import header_logo_layout


def _noop(*_args, **_kwargs) -> None:
    return None


def test_logo_font_family_is_single_fixed_width_family() -> None:
    assert LOGO_FONT_FAMILY == "Consolas"
    assert "," not in LOGO_FONT_FAMILY


def test_theme_headers_render_canonical_assets_without_wrapping() -> None:
    for theme in get_gui_theme_options():
        state = create_gui_state(theme.key, RuntimeConfig(theme=theme.key, backend="mock"))
        layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
        logo_box = layout.content.controls[0].content.controls[0]
        logo_control = logo_text_control_from_box(logo_box)

        assert logo_control.value == header_logo_text(state.theme)
        assert logo_control.font_family == LOGO_FONT_FAMILY
        assert logo_control.style.font_family == LOGO_FONT_FAMILY
        assert logo_control.style.height == header_logo_layout(state.theme).logo_line_height
        assert logo_control.style.letter_spacing == 0
        assert logo_control._Control__attrs["nowrap"][0] is True
        assert logo_control.selectable is False
        assert logo_box.content.scroll is not None or header_logo_layout(state.theme).logo_box_scroll_enabled is False


def test_theme_header_rendering_preserves_body_and_overlay_contracts() -> None:
    state = create_gui_state("janus", RuntimeConfig(theme="janus", backend="mock"))
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    body_row = layout.content.controls[1].content

    assert [control.expand for control in body_row.controls] == [LEFT_COLUMN_FLEX, CENTER_COLUMN_FLEX, RIGHT_COLUMN_FLEX]
    assert hasattr(layout, "diagnostics_drawer")
    assert hasattr(layout, "command_palette")


if __name__ == "__main__":
    test_logo_font_family_is_single_fixed_width_family()
    test_theme_headers_render_canonical_assets_without_wrapping()
    test_theme_header_rendering_preserves_body_and_overlay_contracts()
    print("test_theme_header_rendering PASS")
