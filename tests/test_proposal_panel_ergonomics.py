from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.proposal_panel import build_proposal_panel
from ui.themes.catalog import THEMES


def test_proposal_input_has_hint_shortcut_and_focus_color() -> None:
    panel = build_proposal_panel(THEMES["arasaka"], lambda _proposal: None)
    input_control = panel.content.controls[1]

    assert isinstance(input_control, ft.TextField)
    assert input_control.hint_text == "Enter tribunal proposal..."
    assert input_control.helper_text == "CTRL+ENTER = Submit to Tribunal"
    assert input_control.focused_border_color == THEMES["arasaka"].accent_color
    assert input_control.cursor_color == THEMES["arasaka"].accent_color


if __name__ == "__main__":
    test_proposal_input_has_hint_shortcut_and_focus_color()
    print("test_proposal_panel_ergonomics PASS")
