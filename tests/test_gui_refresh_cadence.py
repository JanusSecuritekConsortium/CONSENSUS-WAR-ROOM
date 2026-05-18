from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.theme_switcher import build_theme_switcher
from ui.flet_app import (
    GUI_ACTIVITY_REFRESH_INTERVAL_SECONDS,
    GUI_INTERACTION_HOLD_SECONDS,
    GUI_PROVIDER_REFRESH_INTERVAL_SECONDS,
    create_gui_state,
)
from ui.themes.catalog import THEMES


def test_gui_background_refresh_is_not_aggressive() -> None:
    assert GUI_ACTIVITY_REFRESH_INTERVAL_SECONDS >= 5.0
    assert GUI_PROVIDER_REFRESH_INTERVAL_SECONDS >= 25.0
    assert GUI_INTERACTION_HOLD_SECONDS >= 10.0


def test_theme_switcher_declares_interaction_callbacks() -> None:
    markers: list[str] = []
    switcher = build_theme_switcher(THEMES["eva"], lambda _: None, on_interaction=lambda: markers.append("held"))

    assert switcher.on_focus is not None
    assert switcher.on_blur is not None

    switcher.on_focus(None)
    switcher.on_blur(None)

    assert markers == ["held", "held"]


def test_gui_state_can_hold_polling_during_footer_interaction() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    state.ui_interaction_hold_until = time.monotonic() + GUI_INTERACTION_HOLD_SECONDS

    assert state.ui_interaction_hold_until > time.monotonic()


if __name__ == "__main__":
    test_gui_background_refresh_is_not_aggressive()
    test_theme_switcher_declares_interaction_callbacks()
    test_gui_state_can_hold_polling_during_footer_interaction()
    print("test_gui_refresh_cadence PASS")
