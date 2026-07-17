from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.verdict_panel import (
    VERDICT_HEADLINE_SIZE,
    VERDICT_PANEL_PADDING,
    VERDICT_PANEL_SPACING,
    VERDICT_REASONING_HEIGHT,
    VERDICT_SYNTHESIS_MAX_LINES,
    VERDICT_TIMELINE_HEIGHT,
    VERDICT_VECTOR_HEIGHT,
    build_verdict_panel,
)
from ui.assets.registry import get_theme_layout_metadata
from ui.components.header import GUI_HEADER_HEIGHT
from ui.layout_contract import FOOTER_HEIGHT, PROPOSAL_HEIGHT
from ui.themes.catalog import THEMES

VIEWPORTS = ((1920, 1080), (1536, 864), (2560, 1440))
BODY_VERTICAL_PADDING = 16
FOOTER_CLEARANCE = 8


def arbiter_content_required_height() -> int:
    text_heights = [
        14,  # panel header row
        20,  # lifecycle banner
        12,  # lifecycle label
        VERDICT_TIMELINE_HEIGHT,
        12,  # current proposal
        VERDICT_HEADLINE_SIZE,
        11,  # lock/link label
        11,  # convergence row
        14,  # confidence row
        12,  # tribunal vector title
        VERDICT_VECTOR_HEIGHT,
        12,  # synthesis title
        VERDICT_SYNTHESIS_MAX_LINES * 14,
        12,  # reasoning title
        VERDICT_REASONING_HEIGHT,
        11,  # context used
        10,  # context summary
    ]
    return (
        (VERDICT_PANEL_PADDING * 2)
        + sum(text_heights)
        + (VERDICT_PANEL_SPACING * (len(text_heights) - 1))
    )


def arbiter_panel_available_height(viewport_height: int, theme_key: str = "janus") -> int:
    body_height = viewport_height - GUI_HEADER_HEIGHT - FOOTER_HEIGHT - BODY_VERTICAL_PADDING
    return body_height - PROPOSAL_HEIGHT - get_theme_layout_metadata(theme_key).proposal_verdict_gap


def arbiter_content_bottom(viewport_height: int, theme_key: str = "janus") -> int:
    top = (
        GUI_HEADER_HEIGHT
        + (BODY_VERTICAL_PADDING // 2)
        + PROPOSAL_HEIGHT
        + get_theme_layout_metadata(theme_key).proposal_verdict_gap
    )
    return top + arbiter_content_required_height()


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


def test_arbiter_content_clears_footer_at_review_viewports() -> None:
    required = arbiter_content_required_height()
    for theme_key in THEMES:
        for _width, viewport_height in VIEWPORTS:
            footer_top = viewport_height - FOOTER_HEIGHT
            available = arbiter_panel_available_height(viewport_height, theme_key)
            content_bottom = arbiter_content_bottom(viewport_height, theme_key)

            assert required <= available - FOOTER_CLEARANCE, (theme_key, viewport_height)
            assert content_bottom <= footer_top - FOOTER_CLEARANCE, (theme_key, viewport_height)


if __name__ == "__main__":
    test_arbiter_verdict_panel_has_fixed_internal_bounds()
    test_arbiter_verdict_panel_does_not_contain_footer_controls()
    test_arbiter_content_clears_footer_at_review_viewports()
    print("test_arbiter_panel_bounds PASS")
