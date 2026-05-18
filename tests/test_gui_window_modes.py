from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from core.cli import resolve_gui_window_mode, resolve_selected_gui_theme
from ui.flet_app import apply_gui_window_mode, create_gui_state


GUI_THEME_INPUTS = ["EVA", "ARASAKA", "WH40K", "HELLDIVERS", "JANUS", "MILITARY"]


class FakeWindow:
    full_screen = False
    maximized = False
    resizable = False


class FakePage:
    def __init__(self) -> None:
        self.window = FakeWindow()
        self.window_full_screen = False
        self.window_maximized = False


def test_default_gui_mode_is_maximized_for_all_themes() -> None:
    for theme in GUI_THEME_INPUTS:
        selected = resolve_selected_gui_theme(theme)
        mode = resolve_gui_window_mode()
        state = create_gui_state(selected, RuntimeConfig(theme=selected, backend="mock"), window_mode=mode)
        page = FakePage()

        apply_gui_window_mode(page, state.window_mode)

        assert state.window_mode == "maximized"
        assert page.window.maximized is True
        assert page.window.full_screen is False


def test_fullscreen_mode_applies_for_all_themes() -> None:
    for theme in GUI_THEME_INPUTS:
        selected = resolve_selected_gui_theme(theme)
        mode = resolve_gui_window_mode(fullscreen=True)
        state = create_gui_state(selected, RuntimeConfig(theme=selected, backend="mock"), window_mode=mode)
        page = FakePage()

        apply_gui_window_mode(page, state.window_mode)

        assert state.window_mode == "fullscreen"
        assert page.window.full_screen is True
        assert page.window.maximized is False


def test_windowed_mode_applies_for_all_themes() -> None:
    for theme in GUI_THEME_INPUTS:
        selected = resolve_selected_gui_theme(theme)
        mode = resolve_gui_window_mode(windowed=True)
        state = create_gui_state(selected, RuntimeConfig(theme=selected, backend="mock"), window_mode=mode)
        page = FakePage()

        apply_gui_window_mode(page, state.window_mode)

        assert state.window_mode == "windowed"
        assert page.window.full_screen is False
        assert page.window.maximized is False


def test_theme_switching_does_not_change_window_mode() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"), window_mode="fullscreen")

    state.theme_key = resolve_selected_gui_theme("ARASAKA")
    state.config.theme = state.theme_key

    assert state.theme_key == "arasaka"
    assert state.window_mode == "fullscreen"


if __name__ == "__main__":
    test_default_gui_mode_is_maximized_for_all_themes()
    test_fullscreen_mode_applies_for_all_themes()
    test_windowed_mode_applies_for_all_themes()
    test_theme_switching_does_not_change_window_mode()
    print("test_gui_window_modes PASS")
