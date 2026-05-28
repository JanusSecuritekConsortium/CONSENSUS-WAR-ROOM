from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for


def test_footer_shortcuts_do_not_share_region_with_theme_selector_or_controls() -> None:
    footer = build_layout_for("helldivers").content.controls[2].content
    left, shortcuts, right = footer.controls

    assert left.width is not None
    assert right.width is not None
    assert shortcuts.expand is True
    assert "Ctrl+K Command" in shortcuts.content.value
    assert "Ctrl+E Export" in shortcuts.content.value
    assert footer.wrap is False
    assert footer.spacing == 0


if __name__ == "__main__":
    test_footer_shortcuts_do_not_share_region_with_theme_selector_or_controls()
    print("test_footer_shortcuts_no_overlap PASS")
