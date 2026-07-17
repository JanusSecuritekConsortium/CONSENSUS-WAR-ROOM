from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.proposal_panel import build_proposal_panel
from ui.themes.catalog import THEMES


def test_proposal_text_area_stays_compact_inside_panel() -> None:
    panel = build_proposal_panel(THEMES["arasaka"], lambda _proposal: None)
    text_fields = [control for control in panel.content.controls if isinstance(control, ft.TextField)]

    assert text_fields
    proposal_input = text_fields[0]
    assert proposal_input.min_lines == 5
    assert proposal_input.max_lines == 7
    assert proposal_input.dense is True
    assert panel.padding.top <= panel.padding.bottom
    assert panel.clip_behavior is not None


if __name__ == "__main__":
    test_proposal_text_area_stays_compact_inside_panel()
    print("test_proposal_panel_internal_spacing PASS")
