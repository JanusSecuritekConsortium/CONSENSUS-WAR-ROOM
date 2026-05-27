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


def test_history_panel_shows_verdict_status_and_dossier_actions() -> None:
    panel = build_proposal_history_viewer(
        make_gui_state("eva"),
        proposals=[
            {
                "proposal_id": "prop_gui",
                "created_at": "2026-05-27T00:00:00Z",
                "title": "GUI status",
                "status": "SUBMITTED",
                "decision_status": "NO_CONSENSUS",
                "decision_timestamp": "2026-05-27T00:01:00Z",
                "linked_verdict_export_json": None,
                "linked_verdict_export_md": None,
            }
        ],
    )
    text = "\n".join(_flatten_text(panel))
    assert "NO_CONSENSUS" in text
    assert "Awaiting tribunal resolution." in text
    assert "EXPORT DOSSIER" in text
    assert "REOPEN DRAFT" in text


if __name__ == "__main__":
    test_history_panel_shows_verdict_status_and_dossier_actions()
    print("test_gui_proposal_verdict_status PASS")
