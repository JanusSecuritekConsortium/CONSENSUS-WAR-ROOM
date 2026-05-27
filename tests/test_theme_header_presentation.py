from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for, header_logo_control_for
from ui.components.header import compact_logo_text, header_logo_layout
from ui.themes.catalog import THEMES


def _logo_box(theme_key: str) -> ft.Container:
    layout = build_layout_for(theme_key)
    return layout.content.controls[0].content.controls[0]


def test_tall_header_logos_use_theme_specific_fit_without_asset_mutation() -> None:
    for theme_key in ("wh40k", "helldivers", "military"):
        logo = header_logo_control_for(theme_key)
        layout = header_logo_layout(THEMES[theme_key])

        assert logo.value == compact_logo_text(THEMES[theme_key])
        assert logo.size == layout.logo_font_size
        assert logo._Control__attrs["nowrap"][0] is True


def test_arasaka_and_janus_header_logos_are_centered_in_box() -> None:
    for theme_key in ("arasaka", "janus"):
        box = _logo_box(theme_key)
        layout = header_logo_layout(THEMES[theme_key])

        assert box.alignment == ft.alignment.center
        assert box.padding.top == layout.logo_top_padding
        assert box.padding.bottom == layout.logo_bottom_padding


if __name__ == "__main__":
    test_tall_header_logos_use_theme_specific_fit_without_asset_mutation()
    test_arasaka_and_janus_header_logos_are_centered_in_box()
    print("test_theme_header_presentation PASS")
