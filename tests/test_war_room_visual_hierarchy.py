from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.proposal_panel import build_proposal_panel
from ui.components.verdict_panel import build_verdict_panel
from ui.themes.catalog import THEMES


def _noop(*_args, **_kwargs) -> None:
    return None


def test_verdict_panel_has_stronger_visual_weight_than_proposal() -> None:
    theme = THEMES["eva"]
    verdict = build_verdict_panel(theme, None)
    proposal = build_proposal_panel(theme, _noop)

    assert verdict.border.top.width == 2
    assert proposal.border.top.width == 1
    assert verdict.padding > proposal.padding
    verdict_text = verdict.content.controls[4]
    assert verdict_text.size >= 32


def test_verdict_panel_has_lifecycle_banner_and_ready_empty_state() -> None:
    panel = build_verdict_panel(THEMES["janus"], None, lifecycle_state="IDLE")
    values = []

    def walk(control) -> None:
        if hasattr(control, "value") and isinstance(control.value, str):
            values.append(control.value)
        if hasattr(control, "content") and control.content is not None:
            walk(control.content)
        for child in getattr(control, "controls", []) or []:
            walk(child)

    walk(panel)
    text = "\n".join(values)

    assert "[IDLE]" in text
    assert "NO ACTIVE PROPOSAL" in text
    assert "TRIBUNAL READY FOR DELIBERATION" in text


if __name__ == "__main__":
    test_verdict_panel_has_stronger_visual_weight_than_proposal()
    test_verdict_panel_has_lifecycle_banner_and_ready_empty_state()
    print("test_war_room_visual_hierarchy PASS")
