from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import TRIBUNAL_AGENT_IDS
from ui.themes.boot_profiles import BOOT_PROFILES
from ui.themes.catalog import THEMES
from ui.animations.boot import build_theme_preview_text


CANONICAL_THEMES = {"military", "eva", "nerv", "wh40k", "helldivers", "arasaka", "janus"}
COLOR_FIELDS = {
    "primary",
    "secondary",
    "accent",
    "background",
    "surface",
    "text",
    "warning",
    "error",
    "muted_text",
    "secondary_text",
    "panel_label",
    "panel_value",
}
INTERFACE_FIELDS = {
    "history",
    "analytics",
    "system_status",
    "vote_status",
    "vote_approve",
    "vote_deny",
    "vote_deadlock",
}


def test_canonical_themes_complete() -> None:
    assert set(THEMES) == CANONICAL_THEMES
    for theme in THEMES.values():
        assert theme.aliases
        assert Path(theme.logo_path).exists(), theme.logo_path
        assert theme.boot_profile_id in BOOT_PROFILES
        assert theme.loading_animation_type
        assert set(theme.palette) == COLOR_FIELDS
        assert set(TRIBUNAL_AGENT_IDS) <= set(theme.monolith_labels)
        assert INTERFACE_FIELDS <= set(theme.interface_labels)
        for labels in theme.monolith_labels.values():
            assert labels["node"]
            assert labels["core"]


def test_previews_do_not_include_global_sections() -> None:
    for key, theme in THEMES.items():
        preview = build_theme_preview_text(theme)
        assert "GLOBAL BOOT SAMPLE" not in preview
        assert "GLOBAL LOADING SAMPLE" not in preview
        assert "THEME BIOS SAMPLE" in preview
        assert "THEME LOADING SAMPLE" in preview
        if key not in {"eva", "nerv"}:
            assert "NERV ARX-7" not in preview
        if key != "arasaka":
            assert "INITIALIZING ARASAKA EXECUTIVE GRID" not in preview


if __name__ == "__main__":
    test_canonical_themes_complete()
    test_previews_do_not_include_global_sections()
    print("test_theme_completeness PASS")
