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
    guidance = panel.content.controls[2]
    assert "CTRL+ENTER = Submit" in guidance.value
    assert input_control.focused_border_color == THEMES["arasaka"].accent_color
    assert input_control.cursor_color == THEMES["arasaka"].accent_color


def test_arasaka_template_dropdown_uses_high_contrast_options() -> None:
    panel = build_proposal_panel(
        THEMES["arasaka"],
        lambda _proposal: None,
        templates=[{"id": "general_tribunal_query", "title": "General Tribunal Query"}],
    )
    dropdown = panel.content.controls[1]

    assert dropdown.data["contrast"] == "arasaka_dark_red"
    assert dropdown.data["selected_state_color"] == "#260407"
    assert dropdown.bgcolor == "#070707"
    assert dropdown.fill_color == "#0f0f0f"
    assert dropdown.focused_border_color == THEMES["arasaka"].accent_color
    assert dropdown.options[0].content.color == THEMES["arasaka"].text_color


if __name__ == "__main__":
    test_proposal_input_has_hint_shortcut_and_focus_color()
    test_arasaka_template_dropdown_uses_high_contrast_options()
    print("test_proposal_panel_ergonomics PASS")
