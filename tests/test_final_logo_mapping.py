from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.animations.bios_boot import generate_bios_boot_lines
from ui.animations.boot import build_theme_preview_text
from config.version import SYSTEM_VERSION
from ui.themes.catalog import THEMES


def test_final_logo_mappings() -> None:
    assert Path(THEMES["eva"].logo_path).name == "nerv_logo.txt"
    assert Path(THEMES["nerv"].logo_path).name == "nerv_logo.txt"
    assert Path(THEMES["arasaka"].logo_path).name == "arasaka_logo.txt"
    assert Path(THEMES["janus"].logo_path).name == "janus_logo.txt"
    assert Path(THEMES["wh40k"].logo_path).name == "cogitator_logo.txt"
    assert Path(THEMES["helldivers"].logo_path).name == "helldivers_logo.txt"
    assert Path(THEMES["military"].logo_path).name == "consensus_logo.txt"


def test_final_supplied_logo_shapes_are_present() -> None:
    wh40k = Path(THEMES["wh40k"].logo_path).read_text(encoding="utf-8")
    helldivers = Path(THEMES["helldivers"].logo_path).read_text(encoding="utf-8")
    military = Path(THEMES["military"].logo_path).read_text(encoding="utf-8")

    assert "████████████████████" in wh40k
    assert "██████████████" in wh40k
    assert len(wh40k.splitlines()) >= 25
    assert "++++++++++++" in helldivers
    assert "++++++       ++++++       ++++ +" in helldivers
    assert len(helldivers.splitlines()) >= 30
    military_lines = military.splitlines()
    assert len(military_lines) == 100
    assert max(len(line) for line in military_lines) == 135
    assert "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@" in military


def test_helldivers_and_janus_use_separate_color_families() -> None:
    helldivers = THEMES["helldivers"]
    janus = THEMES["janus"]

    assert helldivers.primary_color.startswith("#")
    assert janus.primary_color.startswith("#")
    assert helldivers.primary_color != janus.primary_color
    assert helldivers.background_color != janus.background_color
    assert janus.primary_color not in {theme.primary_color for key, theme in THEMES.items() if key != "janus"}


def test_selected_theme_preview_excludes_legacy_cross_theme_sequence() -> None:
    preview = build_theme_preview_text(THEMES["wh40k"])
    assert "THEME BIOS SAMPLE" in preview
    assert "THEME LOADING SAMPLE" in preview
    assert "LEGACY_REFERENCE_SEQUENCE" not in preview
    assert "ARASAKA LOGO" not in preview
    assert "NERV LOGO" not in preview


def test_wh40k_visuals_use_imperial_time_only() -> None:
    preview = build_theme_preview_text(THEMES["wh40k"])
    boot = "\n".join(generate_bios_boot_lines("WH40K", SYSTEM_VERSION))
    text = preview + "\n" + boot

    assert "0918015.M03" in text
    forbidden = ["GMT", "UTC", "14:41", "REAL DATE:", "2026-"]
    for value in forbidden:
        assert value not in text


if __name__ == "__main__":
    test_final_logo_mappings()
    test_final_supplied_logo_shapes_are_present()
    test_helldivers_and_janus_use_separate_color_families()
    test_selected_theme_preview_excludes_legacy_cross_theme_sequence()
    test_wh40k_visuals_use_imperial_time_only()
    print("test_final_logo_mapping PASS")
