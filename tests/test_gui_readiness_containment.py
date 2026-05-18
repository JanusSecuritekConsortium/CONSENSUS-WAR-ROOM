from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from ui.components.monolith_panel import READINESS_ROW_LABELS, build_monolith_panel
from ui.themes.catalog import THEMES


def _wh40k_readiness_panel() -> ft.Control:
    statuses = {key: "ONLINE" for key in [*TRIBUNAL_AGENT_IDS, ARBITER]}
    panel = build_monolith_panel(
        THEMES["wh40k"],
        DEFAULT_NODES,
        statuses,
        memory_status="AVAILABLE",
        provider_status="degraded",
        last_verdict="HUMAN_REVIEW_REQUIRED",
        session_id="wh40k-containment-stress-session",
        lifecycle_state="MONOLITHS DELIBERATING",
    )
    return panel.controls[-1]


def test_readiness_panel_is_bounded_and_clipped() -> None:
    readiness = _wh40k_readiness_panel()

    assert readiness.expand is True
    assert readiness.clip_behavior == ft.ClipBehavior.HARD_EDGE
    assert readiness.content.expand is True


def test_readiness_rows_scroll_inside_panel() -> None:
    readiness = _wh40k_readiness_panel()
    rows_column = readiness.content.controls[1]

    assert rows_column.expand is True
    assert rows_column.scroll == ft.ScrollMode.AUTO
    assert rows_column.tight is True


def test_readiness_rows_use_compact_labels() -> None:
    readiness = _wh40k_readiness_panel()
    rows_column = readiness.content.controls[1]
    labels = [row.controls[1].value for row in rows_column.controls]

    assert tuple(labels) == READINESS_ROW_LABELS
    assert "ACTIVE SESSION" not in labels
    assert "MEMORY STATUS" not in labels
    assert "CURRENT THEME" not in labels
    assert "PROVIDER STATE" not in labels


def test_readiness_values_are_single_line_for_long_wh40k_content() -> None:
    readiness = _wh40k_readiness_panel()
    rows_column = readiness.content.controls[1]

    for row in rows_column.controls:
        value = row.controls[2]
        assert value.expand is True
        assert value.max_lines == 1
        assert value.overflow == ft.TextOverflow.ELLIPSIS


if __name__ == "__main__":
    test_readiness_panel_is_bounded_and_clipped()
    test_readiness_rows_scroll_inside_panel()
    test_readiness_rows_use_compact_labels()
    test_readiness_values_are_single_line_for_long_wh40k_content()
    print("test_gui_readiness_containment PASS")
