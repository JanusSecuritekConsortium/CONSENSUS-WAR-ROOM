from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import make_gui_state
from ui.flet_app import build_proposal_history_viewer


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


def test_proposal_history_panel_lists_actions() -> None:
    state = make_gui_state("eva")
    panel = build_proposal_history_viewer(
        state,
        proposals=[
            {
                "proposal_id": "prop_123",
                "created_at": "2026-05-27T00:00:00Z",
                "title": "Assess risk",
                "status": "SUBMITTED",
                "template_id": "operational_risk",
            }
        ],
    )
    text = "\n".join(_flatten_text(panel))
    assert "PROPOSAL HISTORY" in text
    assert "prop_123" in text
    assert "RESEND" in text
    assert "DUPLICATE/EDIT" in text
    assert "ARCHIVE" in text


if __name__ == "__main__":
    test_proposal_history_panel_lists_actions()
    print("test_proposal_history_panel PASS")
