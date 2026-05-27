from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "text") and isinstance(control.text, str):
        values.append(control.text)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def test_footer_lists_operator_shortcuts() -> None:
    text = "\n".join(_flatten_text(build_layout_for("eva")))
    assert "Ctrl+K Command" in text
    assert "Ctrl+D Diagnostics" in text
    assert "Ctrl+H History" in text
    assert "Ctrl+E Export" in text


if __name__ == "__main__":
    test_footer_lists_operator_shortcuts()
    print("test_footer_shortcuts PASS")
