from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import make_gui_state
from ui.assets.app_icon import APP_ICON_ICO, apply_app_icon_to_page, resolve_app_icon_path
from ui.flet_app import _apply_page_theme


class FakeWindow:
    def __init__(self) -> None:
        self.icon = None


class FakePage:
    def __init__(self) -> None:
        self.window = FakeWindow()


def test_app_icon_resolves_consensus_ico_first() -> None:
    assert resolve_app_icon_path() == APP_ICON_ICO


def test_app_icon_applies_to_flet_window() -> None:
    page = FakePage()

    applied = apply_app_icon_to_page(page)

    assert applied == APP_ICON_ICO
    assert page.window.icon == str(APP_ICON_ICO)


def test_page_theme_configures_window_icon() -> None:
    page = FakePage()
    state = make_gui_state("eva")

    _apply_page_theme(page, state)

    assert page.window.icon == str(APP_ICON_ICO)


if __name__ == "__main__":
    test_app_icon_resolves_consensus_ico_first()
    test_app_icon_applies_to_flet_window()
    test_page_theme_configures_window_icon()
    print("test_app_icon_configured PASS")
