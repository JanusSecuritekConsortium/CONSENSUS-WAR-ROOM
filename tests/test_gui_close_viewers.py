"""Every window opened from the command palette has a CLOSE button, and Esc closes the top one."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import make_gui_state
from tests.test_diagnostics_overlay_reentrant_guard import FakePage
from ui import flet_app as gui

OVERLAY_NAMES = {
    "trace_viewer_open": "decision_trace_viewer",
    "proposal_history_open": "proposal_history_viewer",
    "visual_review_viewer_open": "visual_review_status",
    "telemetry_viewer_open": "telemetry_snapshot",
    "data_sources_viewer_open": "data_sources_viewer",
}


def _find(control, data):
    if getattr(control, "data", None) == data:
        return control
    children = list(getattr(control, "controls", None) or [])
    if getattr(control, "content", None) is not None:
        children.append(control.content)
    for child in children:
        found = _find(child, data)
        if found is not None:
            return found
    return None


def _page():
    state = make_gui_state("janus")
    page = FakePage()
    page.width, page.height = 1280, 720
    page.on_resized = None
    gui._render_page(page, state)
    return page, state


def _overlay(page, name):
    return next((control for control in page.overlay if control.data == name), None)


def test_each_viewer_has_a_close_button_that_closes_it() -> None:
    page, state = _page()
    for flag, name in OVERLAY_NAMES.items():
        setattr(state, flag, True)
        gui._render_page(page, state)
        button = _find(_overlay(page, name), "close_viewer")
        assert button is not None, name
        button.on_click(None)
        assert getattr(state, flag) is False and _overlay(page, name) is None, name


def test_escape_closes_the_top_viewer_first_then_the_palette() -> None:
    page, state = _page()
    page.on_keyboard_event(SimpleNamespace(key="K", ctrl=True))
    state.trace_viewer_open = state.data_sources_viewer_open = True
    gui._render_page(page, state)
    page.on_keyboard_event(SimpleNamespace(key="Escape"))
    assert not state.data_sources_viewer_open and state.trace_viewer_open and state.command_palette_open
    page.on_keyboard_event(SimpleNamespace(key="Escape"))
    assert not state.trace_viewer_open and state.command_palette_open
    page.on_keyboard_event(SimpleNamespace(key="Escape"))
    assert not state.command_palette_open


def test_every_closable_viewer_is_a_real_state_flag() -> None:
    state = make_gui_state("janus")
    for flag in gui.CLOSABLE_VIEWERS:
        assert getattr(state, flag) is False


def test_closing_the_window_ends_the_packaged_app_only() -> None:
    state = make_gui_state("janus")
    exits = []
    gui.finish_after_window_closed(state, frozen=False, exit_process=exits.append)
    assert state.ui_stopped.is_set() and exits == []  # tests and source runs return normally
    gui.finish_after_window_closed(state, frozen=True, exit_process=exits.append)
    assert exits == [0]  # no windowless CONSENSUS.exe left holding the file
