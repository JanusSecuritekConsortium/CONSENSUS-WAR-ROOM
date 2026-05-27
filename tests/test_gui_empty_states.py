from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import noop
from ui.components.proposal_panel import EMPTY_PROPOSAL_HINT, build_proposal_panel
from ui.themes.catalog import THEMES


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


def test_proposal_panel_empty_guidance() -> None:
    panel = build_proposal_panel(THEMES["eva"], noop)
    assert EMPTY_PROPOSAL_HINT in "\n".join(_flatten_text(panel))


if __name__ == "__main__":
    test_proposal_panel_empty_guidance()
    print("test_gui_empty_states PASS")
