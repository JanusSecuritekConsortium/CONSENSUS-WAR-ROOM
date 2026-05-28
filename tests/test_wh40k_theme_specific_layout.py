from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.registry import get_theme_layout_metadata


def test_wh40k_layout_allows_theme_specific_compaction() -> None:
    wh40k = get_theme_layout_metadata("wh40k")
    eva = get_theme_layout_metadata("eva")

    assert wh40k.left_panel_compaction_allowed is True
    assert wh40k.proposal_verdict_gap >= eva.proposal_verdict_gap
    assert wh40k.telemetry_panel_height >= eva.telemetry_panel_height


if __name__ == "__main__":
    test_wh40k_layout_allows_theme_specific_compaction()
    print("test_wh40k_theme_specific_layout PASS")
