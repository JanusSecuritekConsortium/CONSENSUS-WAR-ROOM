from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft

from tests.helpers.gui_harness import make_gui_state
from ui.flet_app import _render_page, set_diagnostics_drawer_open


class FakePage:
    def __init__(self) -> None:
        self.controls = []
        self.overlay = []
        self.title = ""
        self.bgcolor = ""
        self.theme = None
        self.scroll = "auto"
        self.padding = 10
        self.spacing = 10
        self.window = type("Window", (), {})()
        self.on_keyboard_event = None
        self.update_count = 0

    def add(self, control) -> None:
        self.controls.append(control)

    def update(self, *controls) -> None:
        self.update_count += 1

    def run_thread(self, target, *args, **kwargs) -> None:
        target(*args, **kwargs)

    def close(self) -> None:
        return None


def test_diagnostics_overlay_replaces_existing_overlay_without_stacking() -> None:
    state = make_gui_state("janus")
    page = FakePage()
    page.overlay.append(ft.Container(data="diagnostics_drawer"))
    set_diagnostics_drawer_open(state, True)

    _render_page(page, state)
    _render_page(page, state)

    diagnostics = [control for control in page.overlay if getattr(control, "data", None) == "diagnostics_drawer"]
    assert len(diagnostics) == 1
    assert page.update_count == 2


if __name__ == "__main__":
    test_diagnostics_overlay_replaces_existing_overlay_without_stacking()
    print("test_diagnostics_overlay_reentrant_guard PASS")


def test_diagnostics_closes_by_cross_and_footer_toggle():
    from ui.flet_app import FOOTER_HEIGHT

    state = make_gui_state("janus")
    page = FakePage()
    _render_page(page, state)

    def diagnostics_button():
        footer = page.controls[0].content.controls[2].content
        return footer.controls[2].content.controls[0]

    def drawer():
        return next(c for c in page.overlay if c.data == "diagnostics_drawer")

    diagnostics_button().on_click(None)
    assert state.diagnostics_drawer_open
    panel = drawer()
    assert panel.bottom > FOOTER_HEIGHT  # Overlay cannot intercept the footer.
    assert panel.top is not None and panel.right is not None and panel.width == 380
    close = panel.content.controls[0].controls[0]
    assert close.tooltip == "Close diagnostics"
    close.on_click(None)
    assert not state.diagnostics_drawer_open
    assert not any(c.data == "diagnostics_drawer" for c in page.overlay)

    diagnostics_button().on_click(None)
    assert state.diagnostics_drawer_open
    diagnostics_button().on_click(None)
    assert not state.diagnostics_drawer_open
    assert not any(c.data == "diagnostics_drawer" for c in page.overlay)
