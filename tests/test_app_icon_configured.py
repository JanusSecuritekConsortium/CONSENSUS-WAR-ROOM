from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import make_gui_state
from ui.assets.app_icon import APP_ICON_ICO, apply_app_icon_to_page, resolve_app_icon_path
from ui.assets.brand import CORPORATE_SYMBOL, corporate_symbol_base64, validate_brand_assets
from ui.components.header import build_header
from ui.themes.catalog import THEMES
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


def test_corporate_c2_is_visible_across_themes_and_separate_from_desktop_icon() -> None:
    import base64
    import flet as ft
    from ui.assets.app_icon import APP_ICON_PNG_256

    def walk(control):
        yield control
        for child in control._get_children():
            yield from walk(child)

    assert not validate_brand_assets()
    assert CORPORATE_SYMBOL.read_bytes() != APP_ICON_PNG_256.read_bytes()
    for theme in THEMES.values():
        header = build_header(theme, "READY", "AVAILABLE")
        marks = [control for control in walk(header)
                 if isinstance(control, ft.Image) and isinstance(control.data, dict)
                 and control.data.get("role") == "corporate_logo"]
        assert len(marks) == 1
        assert marks[0].data["identity"] == "C2"
        assert base64.b64decode(marks[0].src_base64) == CORPORATE_SYMBOL.read_bytes()
        assert marks[0].color == theme.primary_color
        assert corporate_symbol_base64() == marks[0].src_base64


if __name__ == "__main__":
    test_app_icon_resolves_consensus_ico_first()
    test_app_icon_applies_to_flet_window()
    test_page_theme_configures_window_icon()
    print("test_app_icon_configured PASS")
