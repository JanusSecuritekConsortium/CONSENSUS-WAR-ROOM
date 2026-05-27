from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.proposal_panel import build_proposal_panel
from ui.themes.catalog import THEMES


def test_proposal_panel_uses_tight_spacing_and_balanced_padding() -> None:
    panel = build_proposal_panel(THEMES["eva"], lambda _proposal: None)

    assert panel.content.spacing <= 7
    assert panel.content.tight is True
    assert panel.padding.top <= panel.padding.bottom


if __name__ == "__main__":
    test_proposal_panel_uses_tight_spacing_and_balanced_padding()
    print("test_proposal_panel_spacing PASS")
