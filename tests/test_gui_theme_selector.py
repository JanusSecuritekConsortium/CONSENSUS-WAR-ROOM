from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from core.cli import resolve_selected_gui_theme
from ui.components.theme_switcher import THEME_SWITCHER_WIDTH, build_theme_switcher
from ui.flet_app import create_gui_state
from ui.themes.catalog import THEMES, get_gui_theme_key, get_gui_theme_options, resolve_theme_key


EXPECTED_GUI_THEME_NAMES = {
    "Arasaka Executive Tribunal",
    "MAGI Consensus Array",
    "Managed Democracy Tribunal",
    "Janus Security Consortium",
    "CONSENSUS War Room",
    "Cogitator Tribunal",
}


def test_gui_selector_has_deduplicated_visual_families() -> None:
    options = get_gui_theme_options()
    names = [theme.display_name for theme in options]
    keys = [theme.key for theme in options]

    assert set(names) == EXPECTED_GUI_THEME_NAMES
    assert len(names) == len(set(names)) == 6
    assert "nerv" not in keys
    assert "NERV Tribunal Interlock" not in names


def test_nerv_still_resolves_but_gui_family_is_magi() -> None:
    assert resolve_theme_key("NERV") == "nerv"
    assert resolve_theme_key("EVA") == "eva"
    assert get_gui_theme_key("NERV") == "eva"
    assert get_gui_theme_key("EVA/NERV") == "eva"


def test_theme_switcher_hides_aliases_and_uses_display_names() -> None:
    seen: list[str] = []
    switcher = build_theme_switcher(THEMES["nerv"], seen.append)
    option_names = [option.text for option in switcher.options]
    option_keys = [option.key for option in switcher.options]

    assert switcher.value == "eva"
    assert switcher.width == THEME_SWITCHER_WIDTH
    assert switcher.dense is True
    assert set(option_names) == EXPECTED_GUI_THEME_NAMES
    assert "nerv" not in option_keys
    assert not any("NERV" in name for name in option_names)


def test_gui_magi_option_applies_eva_nerv_visual_family() -> None:
    state = create_gui_state("MAGI", RuntimeConfig(theme="eva", backend="mock"))

    assert state.theme_key == "eva"
    assert Path(state.theme.logo_path).name == "nerv_logo.txt"
    assert state.theme.monolith_labels == THEMES["nerv"].monolith_labels


def test_gui_boot_selection_and_runtime_theme_stay_aligned() -> None:
    selected = resolve_selected_gui_theme("NERV", seed=42)
    state = create_gui_state(selected, RuntimeConfig(theme=selected, backend="mock"))

    assert selected == "eva"
    assert state.theme_key == selected
    assert state.config.theme == selected


if __name__ == "__main__":
    test_gui_selector_has_deduplicated_visual_families()
    test_nerv_still_resolves_but_gui_family_is_magi()
    test_theme_switcher_hides_aliases_and_uses_display_names()
    test_gui_magi_option_applies_eva_nerv_visual_family()
    test_gui_boot_selection_and_runtime_theme_stay_aligned()
    print("test_gui_theme_selector PASS")
