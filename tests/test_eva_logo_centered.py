from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.header import header_logo_layout
from ui.themes.catalog import THEMES


def test_eva_header_logo_uses_centered_non_scroll_layout() -> None:
    logo_box = build_layout_for("eva").content.controls[0].content.controls[0]
    layout = header_logo_layout(THEMES["eva"])

    assert layout.logo_horizontal_align == "center"
    assert layout.logo_vertical_align == "center"
    assert layout.logo_box_scroll_enabled is False
    assert logo_box.content.scroll is None


if __name__ == "__main__":
    test_eva_header_logo_uses_centered_non_scroll_layout()
    print("test_eva_logo_centered PASS")
