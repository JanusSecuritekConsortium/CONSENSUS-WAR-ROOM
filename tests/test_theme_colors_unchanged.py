from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.themes.catalog import THEMES


EXPECTED_THEME_COLORS = {
    "military": ("#39ff14", "#9bbf9b", "#ffbf00", "#050806", "#101810", "#d8ffe0", "#ffbf00", "#ff3b30"),
    "eva": ("#ff8a00", "#ff2d20", "#00d5ff", "#100302", "#220b06", "#fff2df", "#ff9b00", "#ff2d20"),
    "nerv": ("#ff5400", "#b11226", "#ffffff", "#110607", "#211010", "#fff4e8", "#ff9d00", "#ff1f1f"),
    "wh40k": ("#ffd76a", "#d5452f", "#fff1b8", "#050403", "#120e08", "#fff7df", "#ffcc4d", "#d43a2f"),
    "helldivers": ("#ffd100", "#2da1ff", "#f5f5f5", "#020812", "#06172b", "#f2fbff", "#ffd100", "#ff3b30"),
    "arasaka": ("#ff1f2d", "#1a1a1a", "#f5f5f5", "#050505", "#151515", "#f2f2f2", "#ffb000", "#ff1f2d"),
    "janus": ("#ff58e3", "#8f4bb0", "#f9d2ff", "#0b0610", "#190923", "#fff0ff", "#d9a2ff", "#ff5f57"),
}


def test_theme_colors_remain_unchanged_for_visual_refinement_pass() -> None:
    for theme_key, expected in EXPECTED_THEME_COLORS.items():
        theme = THEMES[theme_key]
        actual = (
            theme.primary_color,
            theme.secondary_color,
            theme.accent_color,
            theme.background_color,
            theme.surface_color,
            theme.text_color,
            theme.warning_color,
            theme.error_color,
        )

        assert actual == expected, theme_key


if __name__ == "__main__":
    test_theme_colors_remain_unchanged_for_visual_refinement_pass()
    print("test_theme_colors_unchanged PASS")
