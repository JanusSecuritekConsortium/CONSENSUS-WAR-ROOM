from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.theme_switcher import THEME_SWITCHER_WIDTH


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def test_footer_keeps_diagnostics_button_visible_in_right_region() -> None:
    footer = build_layout_for("arasaka").content.controls[2].content
    left, shortcuts, right = footer.controls
    values = [getattr(control, "text", None) or getattr(control, "value", None) for control in _walk(right)]

    assert left.width == THEME_SWITCHER_WIDTH
    assert right.width == 125
    assert shortcuts.expand is True
    assert "DIAGNOSTICS" in values
    assert right.clip_behavior is not None


def test_footer_has_no_aurelius_voice_control() -> None:
    footer = build_layout_for("eva").content.controls[2]
    values = [str(getattr(control, "label", "") or getattr(control, "value", "") or getattr(control, "text", "")) for control in _walk(footer)]

    assert all("AURELIUS" not in value for value in values)


if __name__ == "__main__":
    test_footer_keeps_diagnostics_button_visible_in_right_region()
    test_footer_has_no_aurelius_voice_control()
    print("test_footer_diagnostics_visibility PASS")
