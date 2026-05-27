from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.header import GUI_LOGO_BOX_HEIGHT
from ui.themes.catalog import THEMES
from ui.components.header import header_logo_layout


def _logo_box(theme_key: str) -> ft.Container:
    layout = build_layout_for(theme_key)
    return layout.content.controls[0].content.controls[0]


def test_manual_reviewed_themes_have_balanced_vertical_padding() -> None:
    for theme_key in ("arasaka", "military", "janus"):
        box = _logo_box(theme_key)
        layout = header_logo_layout(THEMES[theme_key])

        assert box.alignment == ft.alignment.center
        assert box.height == GUI_LOGO_BOX_HEIGHT
        assert box.padding.top == layout.logo_top_padding
        assert box.padding.bottom == layout.logo_bottom_padding
        assert box.padding.top >= box.padding.bottom


def test_tall_logos_use_reduced_font_sizes_for_full_visibility() -> None:
    assert header_logo_layout(THEMES["wh40k"]).logo_font_size >= 7
    assert header_logo_layout(THEMES["helldivers"]).logo_font_size <= 5
    assert header_logo_layout(THEMES["military"]).logo_font_size <= 9


if __name__ == "__main__":
    test_manual_reviewed_themes_have_balanced_vertical_padding()
    test_tall_logos_use_reduced_font_sizes_for_full_visibility()
    print("test_header_logo_vertical_offsets PASS")
