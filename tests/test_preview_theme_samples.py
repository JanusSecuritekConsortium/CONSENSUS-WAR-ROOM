from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.animations.boot import build_theme_preview_text
from ui.animations.loading import get_loading_style
from ui.themes.catalog import THEMES


EXPECTED_LOADING_MARKERS = {
    "military": "TACTICAL GREEN BAR",
    "eva": "MAGI-LINK SYNCHRONIZATION",
    "nerv": "NERV MAGI-LINK INTERLOCK",
    "wh40k": "COGITATOR RITE AND LITANY",
    "helldivers": "LIBERTY AND DEMOCRACY BAR",
    "arasaka": "CORPORATE CLEARANCE GRID",
    "janus": "DUAL-FRONT MIRROR SYNC",
}


def test_preview_uses_selected_theme_logo_and_samples_only() -> None:
    nerv_logo = Path(THEMES["nerv"].logo_path).read_text(encoding="utf-8").rstrip("\n")
    arasaka_logo = Path(THEMES["arasaka"].logo_path).read_text(encoding="utf-8").rstrip("\n")

    for key, theme in THEMES.items():
        preview = build_theme_preview_text(theme)
        expected_logo = Path(theme.logo_path).read_text(encoding="utf-8").rstrip("\n")

        assert preview.startswith(expected_logo)
        assert preview.count(expected_logo) == 1
        assert EXPECTED_LOADING_MARKERS[key] in preview
        assert f"[LOAD:{get_loading_style(key).key}]" in preview
        assert "GLOBAL BOOT SAMPLE" not in preview
        assert "GLOBAL LOADING SAMPLE" not in preview
        assert "THEME BIOS SAMPLE" in preview

        if key not in {"eva", "nerv"}:
            assert nerv_logo not in preview
        if key != "arasaka":
            assert arasaka_logo not in preview


def test_preview_bios_sample_does_not_repeat_logo() -> None:
    for theme in THEMES.values():
        preview = build_theme_preview_text(theme)
        expected_logo = Path(theme.logo_path).read_text(encoding="utf-8").rstrip("\n")
        bios_sample = preview.split("THEME BIOS SAMPLE", 1)[1].split("THEME LOADING SAMPLE", 1)[0]

        assert expected_logo not in bios_sample


def test_preview_includes_selected_loading_style_only() -> None:
    for key, theme in THEMES.items():
        preview = build_theme_preview_text(theme)
        style = get_loading_style(key)
        loading_sample = preview.split("THEME LOADING SAMPLE", 1)[1]

        assert f"[LOAD:{style.key}]" in loading_sample
        for other_key in THEMES:
            other_style = get_loading_style(other_key)
            if other_key != key:
                assert f"[LOAD:{other_style.key}]" not in loading_sample


if __name__ == "__main__":
    test_preview_uses_selected_theme_logo_and_samples_only()
    test_preview_bios_sample_does_not_repeat_logo()
    test_preview_includes_selected_loading_style_only()
    print("test_preview_theme_samples PASS")
