from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.theme_switcher import THEME_SWITCHER_WIDTH


def _footer_row(theme_key: str):
    return build_layout_for(theme_key).content.controls[2].content


def test_footer_shortcuts_are_center_region_for_all_themes() -> None:
    for theme_key in ("eva", "arasaka", "janus", "wh40k", "helldivers", "military"):
        footer = _footer_row(theme_key)
        left, shortcuts, right = footer.controls

        assert left.width == THEME_SWITCHER_WIDTH
        assert right.width == 125
        assert shortcuts.expand is True
        assert shortcuts.data["role"] == "footer_shortcuts"
        assert shortcuts.data["alignment"] == "center"
        assert shortcuts.content.text_align.name == "CENTER"


if __name__ == "__main__":
    test_footer_shortcuts_are_center_region_for_all_themes()
    print("test_footer_shortcuts_centered PASS")
