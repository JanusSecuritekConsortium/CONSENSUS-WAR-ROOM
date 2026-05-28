from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.header import GUI_LOGO_BOX_HEIGHT, GUI_LOGO_BOX_MAX_WIDTH, header_logo_layout, theme_header_height
from ui.themes.catalog import get_gui_theme_options


def test_header_containers_have_stable_constraints() -> None:
    for theme in get_gui_theme_options():
        layout = build_layout_for(theme.key)
        header = layout.content.controls[0]
        logo_box = header.content.controls[0]

        assert header.height == theme_header_height(theme)
        assert logo_box.height == (header_logo_layout(theme).logo_box_height or GUI_LOGO_BOX_HEIGHT)
        assert 360 <= logo_box.width <= GUI_LOGO_BOX_MAX_WIDTH
        assert logo_box.clip_behavior is not None


if __name__ == "__main__":
    test_header_containers_have_stable_constraints()
    print("test_header_container_constraints PASS")
