from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.animations.boot import build_theme_preview_text
from ui.animations.loading import LOADING_STYLES, get_loading_style, loading_delay
from ui.themes.catalog import THEMES


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def test_each_theme_has_unique_loading_style_id() -> None:
    style_ids = []
    for key, theme in THEMES.items():
        style = get_loading_style(key)
        style_ids.append(style.key)
        assert theme.loading_animation_type == style.key

    assert len(style_ids) == len(set(style_ids))
    assert set(LOADING_STYLES) == set(THEMES)


def test_each_theme_has_theme_specific_loading_stages() -> None:
    expected_stage_markers = {
        "military": ["SYSTEM CHECK", "COMMS", "MONOLITH LINK", "TACTICAL BUS"],
        "eva": ["MAGI LINK", "SYNCHRONIZATION RATE", "PATTERN ANALYSIS", "INTERLOCK BUS"],
        "nerv": ["MAGI LINK", "SYNCHRONIZATION RATE", "PATTERN ANALYSIS", "INTERLOCK BUS"],
        "arasaka": ["SECURITY CLEARANCE", "COUNTERINTELLIGENCE GRID", "CORPORATE NODE", "BOARD VERDICT CHANNEL"],
        "janus": ["DUAL CHANNEL", "ANALYTIC MIRROR", "COUNTERPART SYNC", "REVERSIBILITY CHECK"],
        "wh40k": ["MACHINE SPIRIT", "NOOSPHERIC LINK", "DATA-VAULT", "SANCTION PROTOCOL"],
        "helldivers": ["DEMOCRATIC AUTHORIZATION", "LIBERTY LOGIC", "REQUISITION ACCOUNTING", "STRATAGEM SAFETY"],
    }
    for key, expected in expected_stage_markers.items():
        style = get_loading_style(key)
        assert len(style.stages) >= 4
        for marker in expected:
            assert marker in style.stages


def test_wh40k_loading_uses_imperial_visual_language_only() -> None:
    preview = build_theme_preview_text(THEMES["wh40k"])
    loading_sample = preview.split("THEME LOADING SAMPLE", 1)[1]

    assert "MACHINE SPIRIT" in loading_sample
    assert "NOOSPHERIC LINK" in loading_sample
    for forbidden in ["UTC", "GMT", "T00:", "Z"]:
        assert forbidden not in loading_sample


def test_random_speed_can_be_seeded_deterministically() -> None:
    first = loading_delay("random", seed=42)
    second = loading_delay("random", seed=42)
    third = loading_delay("random", seed=43)

    assert first == second
    assert first != third
    assert 0.015 <= first <= 0.06


def test_text_previews_do_not_export_ansi_color_codes() -> None:
    for theme in THEMES.values():
        preview = build_theme_preview_text(theme)
        assert not ANSI_RE.search(preview), theme.key


if __name__ == "__main__":
    test_each_theme_has_unique_loading_style_id()
    test_each_theme_has_theme_specific_loading_stages()
    test_wh40k_loading_uses_imperial_visual_language_only()
    test_random_speed_can_be_seeded_deterministically()
    test_text_previews_do_not_export_ansi_color_codes()
    print("test_theme_loading_bars PASS")
