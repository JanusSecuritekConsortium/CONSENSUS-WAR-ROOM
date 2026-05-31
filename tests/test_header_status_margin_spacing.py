from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.header import build_header
from ui.themes.catalog import get_gui_theme_options


def test_status_panel_preserves_lower_margin_for_every_theme() -> None:
    for theme in get_gui_theme_options():
        header = build_header(theme, "ready", "available")
        status_panel = header.content.controls[1]
        assert status_panel.padding.bottom > status_panel.padding.top
        assert status_panel.content.spacing <= 2


if __name__ == "__main__":
    test_status_panel_preserves_lower_margin_for_every_theme()
    print("test_header_status_margin_spacing PASS")
