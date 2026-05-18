from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from core.cli import resolve_selected_theme
from ui.flet_app import create_gui_state
from ui.themes.catalog import THEMES


def test_gui_theme_state_matches_boot_selected_theme() -> None:
    selected = resolve_selected_theme(None, seed=42)
    state = create_gui_state(selected, RuntimeConfig(theme=selected, backend="mock"))

    assert state.theme_key == selected
    assert state.config.theme == selected
    assert state.theme == THEMES[selected]


def test_eva_nerv_share_visual_family() -> None:
    eva = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    nerv = create_gui_state("NERV", RuntimeConfig(theme="nerv", backend="mock"))

    assert Path(eva.theme.logo_path).name == "nerv_logo.txt"
    assert Path(nerv.theme.logo_path).name == "nerv_logo.txt"
    assert eva.theme.monolith_labels == nerv.theme.monolith_labels


def test_arasaka_remains_separate_visual_family() -> None:
    arasaka = create_gui_state("ARASAKA", RuntimeConfig(theme="arasaka", backend="mock"))
    eva = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))

    assert Path(arasaka.theme.logo_path).name == "arasaka_logo.txt"
    assert arasaka.theme.logo_path != eva.theme.logo_path
    assert arasaka.theme.primary_color != eva.theme.primary_color


if __name__ == "__main__":
    test_gui_theme_state_matches_boot_selected_theme()
    test_eva_nerv_share_visual_family()
    test_arasaka_remains_separate_visual_family()
    print("test_gui_theme_binding PASS")
