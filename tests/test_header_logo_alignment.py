from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.themes.catalog import get_gui_theme_options


def test_header_logo_boxes_are_center_aligned() -> None:
    for theme in get_gui_theme_options():
        layout = build_layout_for(theme.key)
        logo_box = layout.content.controls[0].content.controls[0]

        assert logo_box.alignment == ft.alignment.center
        assert logo_box.content.horizontal_alignment == ft.CrossAxisAlignment.CENTER


if __name__ == "__main__":
    test_header_logo_boxes_are_center_aligned()
    print("test_header_logo_alignment PASS")
