from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.header import logo_box_border_color
from ui.themes.catalog import THEMES


def _logo_box(theme_key: str) -> ft.Container:
    layout = build_layout_for(theme_key)
    return layout.content.controls[0].content.controls[0]


def test_arasaka_logo_box_has_a_visible_red_frame() -> None:
    theme = THEMES["arasaka"]
    box = _logo_box("arasaka")

    assert box.data["role"] == "header_logo_viewport"
    assert box.border.top.color == theme.primary_color
    assert box.border.left.color == theme.primary_color


def test_other_themes_keep_their_secondary_logo_frame() -> None:
    for key, theme in THEMES.items():
        if key == "arasaka":
            continue
        assert logo_box_border_color(theme) == theme.secondary_color, key
