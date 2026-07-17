from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.header import GUI_LOGO_BOX_HEIGHT, header_logo_layout, theme_header_height, theme_header_split, theme_logo_layout_mode
from ui.themes.catalog import get_gui_theme_options


def test_header_containers_have_stable_constraints() -> None:
    for theme in get_gui_theme_options():
        layout = build_layout_for(theme.key)
        header = layout.content.controls[0]
        logo_box = header.content.controls[0]

        assert header.height == theme_header_height(theme)
        mode = theme_logo_layout_mode(theme)["mode"]
        if mode == "percentage":
            assert logo_box.height == GUI_LOGO_BOX_HEIGHT
            assert logo_box.expand == theme_header_split(theme)[0]
            assert logo_box.width is None
        elif mode in {"square", "supersampled_square"}:
            assert logo_box.height == GUI_LOGO_BOX_HEIGHT
            assert logo_box.expand is None
            assert logo_box.width == GUI_LOGO_BOX_HEIGHT
        elif mode in {"supersampled_rect", "supersampled_banner"}:
            logo_layout = header_logo_layout(theme)
            assert logo_box.height == (logo_layout.logo_box_height or GUI_LOGO_BOX_HEIGHT)
            assert logo_box.expand is None
            assert logo_box.width == logo_layout.logo_box_width
        elif mode == "historical":
            assert logo_box.height == GUI_LOGO_BOX_HEIGHT
            assert logo_box.expand is None
            assert logo_box.width is not None
        assert logo_box.clip_behavior is not None


if __name__ == "__main__":
    test_header_containers_have_stable_constraints()
    print("test_header_container_constraints PASS")
