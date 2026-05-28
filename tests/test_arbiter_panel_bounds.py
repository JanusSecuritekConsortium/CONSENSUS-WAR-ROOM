from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.verdict_panel import (
    VERDICT_PANEL_PADDING,
    VERDICT_PANEL_SPACING,
    VERDICT_REASONING_HEIGHT,
    VERDICT_TIMELINE_HEIGHT,
    VERDICT_VECTOR_HEIGHT,
    build_verdict_panel,
)
from ui.themes.catalog import THEMES


def _find_by_role(control, role: str):
    if getattr(control, "data", None) == {"role": role} or (
        isinstance(getattr(control, "data", None), dict) and control.data.get("role") == role
    ):
        return control
    content = getattr(control, "content", None)
    if content is not None:
        found = _find_by_role(content, role)
        if found is not None:
            return found
    for child in getattr(control, "controls", []) or []:
        found = _find_by_role(child, role)
        if found is not None:
            return found
    return None


def test_arbiter_verdict_panel_has_fixed_internal_bounds() -> None:
    panel = build_verdict_panel(
        THEMES["janus"],
        None,
        lifecycle_state="ANALYZING",
        reasoning_events=[f"event {index}" for index in range(20)],
    )

    assert panel.data == {"role": "arbiter_verdict_panel"}
    assert panel.padding == VERDICT_PANEL_PADDING
    assert panel.content.spacing == VERDICT_PANEL_SPACING
    assert panel.clip_behavior is not None
    assert _find_by_role(panel, "verdict_phase_timeline").height == VERDICT_TIMELINE_HEIGHT
    assert _find_by_role(panel, "verdict_vote_vector").height == VERDICT_VECTOR_HEIGHT
    assert _find_by_role(panel, "verdict_reasoning_stream").height == VERDICT_REASONING_HEIGHT


def test_arbiter_verdict_panel_does_not_contain_footer_controls() -> None:
    panel = build_verdict_panel(THEMES["arasaka"], None)
    values: list[str] = []

    def walk(control) -> None:
        for attr in ("value", "text", "label"):
            value = getattr(control, attr, None)
            if isinstance(value, str):
                values.append(value)
        content = getattr(control, "content", None)
        if content is not None:
            walk(content)
        for child in getattr(control, "controls", []) or []:
            walk(child)

    walk(panel)
    joined = "\n".join(values)
    assert "AURELIUS" not in joined
    assert "DIAGNOSTICS" not in joined


if __name__ == "__main__":
    test_arbiter_verdict_panel_has_fixed_internal_bounds()
    test_arbiter_verdict_panel_does_not_contain_footer_controls()
    print("test_arbiter_panel_bounds PASS")
