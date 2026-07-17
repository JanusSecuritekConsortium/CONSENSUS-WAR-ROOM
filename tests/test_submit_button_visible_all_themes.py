from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.flet_app import PROPOSAL_HEIGHT
from ui.themes.catalog import GUI_THEME_KEYS

PROPOSAL_BOTTOM_CLEARANCE = 8
PROPOSAL_PANEL_VERTICAL_PADDING = 16
PROPOSAL_PANEL_SPACING = 5
PROPOSAL_TITLE_HEIGHT = 14
PROPOSAL_DROPDOWN_HEIGHT = 48
PROPOSAL_INPUT_HEIGHT = 90
PROPOSAL_HELPER_HEIGHT = 12
PROPOSAL_BUTTON_HEIGHT = 36


def proposal_submit_button_bottom_margin() -> int:
    content_height = (
        PROPOSAL_PANEL_VERTICAL_PADDING
        + PROPOSAL_TITLE_HEIGHT
        + PROPOSAL_DROPDOWN_HEIGHT
        + PROPOSAL_INPUT_HEIGHT
        + PROPOSAL_HELPER_HEIGHT
        + PROPOSAL_BUTTON_HEIGHT
        + (PROPOSAL_PANEL_SPACING * 4)
    )
    return PROPOSAL_HEIGHT - content_height


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def _proposal_region(layout: ft.Control) -> ft.Control:
    body_row = layout.content.controls[1].content
    center_column = body_row.controls[1].content
    return center_column.controls[0]


def test_submit_button_is_visible_inside_proposal_panel_for_all_themes() -> None:
    for theme_key in GUI_THEME_KEYS:
        region = _proposal_region(build_layout_for(theme_key))
        controls = list(_walk(region))
        submit_buttons = [
            control
            for control in controls
            if getattr(control, "data", None) == {"role": "submit_to_tribunal_button"}
            or getattr(control, "text", None) == "SUBMIT TO TRIBUNAL"
        ]
        proposal_inputs = [
            control
            for control in controls
            if getattr(control, "data", None) == {"role": "proposal_input"}
        ]

        assert submit_buttons, f"{theme_key} proposal submit button missing"
        assert proposal_inputs, f"{theme_key} proposal input missing"
        assert region.clip_behavior is not None
        assert region.height == PROPOSAL_HEIGHT
        assert PROPOSAL_HEIGHT >= 270
        assert getattr(submit_buttons[0], "height", None) <= 40
        assert getattr(proposal_inputs[0], "min_lines", None) >= 5
        assert proposal_submit_button_bottom_margin() >= PROPOSAL_BOTTOM_CLEARANCE


if __name__ == "__main__":
    test_submit_button_is_visible_inside_proposal_panel_for_all_themes()
    print("test_submit_button_visible_all_themes PASS")
