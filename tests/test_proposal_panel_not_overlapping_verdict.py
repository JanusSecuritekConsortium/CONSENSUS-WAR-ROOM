from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.assets.registry import get_theme_layout_metadata
from ui.flet_app import PROPOSAL_HEIGHT


def test_proposal_and_verdict_regions_have_explicit_gap() -> None:
    layout = build_layout_for("eva")
    center_column = layout.content.controls[1].content.controls[1].content
    proposal_region, verdict_region = center_column.controls
    metadata = get_theme_layout_metadata("eva")

    assert center_column.spacing == metadata.proposal_verdict_gap
    assert proposal_region.data["role"] == "proposal_panel_region"
    assert verdict_region.data["role"] == "verdict_panel_region"
    assert proposal_region.expand is None
    assert proposal_region.height == PROPOSAL_HEIGHT
    assert verdict_region.expand is True


if __name__ == "__main__":
    test_proposal_and_verdict_regions_have_explicit_gap()
    print("test_proposal_panel_not_overlapping_verdict PASS")
