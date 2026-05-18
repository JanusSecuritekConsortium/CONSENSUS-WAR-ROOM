from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.log_panel import log_level_color_category
from ui.components.monolith_panel import status_color, status_color_category
from ui.themes.catalog import THEMES


def test_monolith_status_color_categories() -> None:
    assert status_color_category("ONLINE") == "success"
    assert status_color_category("THINKING") == "thinking"
    assert status_color_category("DEGRADED") == "warning"
    assert status_color_category("OFFLINE") == "error"
    assert status_color_category("ERROR") == "error"


def test_monolith_status_colors_use_theme_palette() -> None:
    theme = THEMES["eva"]

    assert status_color(theme, "ONLINE") == theme.primary_color
    assert status_color(theme, "THINKING") == theme.accent_color
    assert status_color(theme, "DEGRADED") == theme.warning_color
    assert status_color(theme, "ERROR") == theme.error_color


def test_log_level_color_categories() -> None:
    assert log_level_color_category("[12:00:00] INFO system_command") == "info"
    assert log_level_color_category("[12:00:00] WARN msty_runtime_health") == "warning"
    assert log_level_color_category("[12:00:00] ERROR vote_error") == "error"
    assert log_level_color_category("[12:00:00] OK active_compile") == "success"
    assert log_level_color_category("[12:00:00] INFO vote") == "decision"
    assert log_level_color_category("[12:00:00] INFO verdict") == "decision"


if __name__ == "__main__":
    test_monolith_status_color_categories()
    test_monolith_status_colors_use_theme_palette()
    test_log_level_color_categories()
    print("test_gui_status_colors PASS")
