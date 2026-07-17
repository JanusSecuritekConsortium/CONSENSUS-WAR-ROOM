from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.header import GUI_LOGO_BOX_HEIGHT, logo_runtime_diagnostics, theme_logo_layout_mode
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
        mode = theme_logo_layout_mode(THEMES[theme_key])["mode"]
        expected_top = 0 if mode.startswith("supersampled") else layout.logo_top_padding
        expected_bottom = 0 if mode.startswith("supersampled") else layout.logo_bottom_padding
        assert box.padding.top == expected_top
        assert box.padding.bottom == expected_bottom
        assert box.padding.top >= box.padding.bottom


def test_tall_logos_fit_their_resolved_viewports() -> None:
    for theme_key in ("wh40k", "helldivers", "military"):
        diagnostics = logo_runtime_diagnostics(theme_key)

        assert diagnostics["visible_artwork_width"] <= diagnostics["logo_region_width"]
        assert diagnostics["visible_artwork_height"] <= diagnostics["logo_region_height"]
        assert min(diagnostics["clearances"]) >= 0


if __name__ == "__main__":
    test_manual_reviewed_themes_have_balanced_vertical_padding()
    test_tall_logos_fit_their_resolved_viewports()
    print("test_header_logo_vertical_offsets PASS")
