from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import CENTER_COLUMN_FLEX, LEFT_COLUMN_FLEX, RIGHT_COLUMN_FLEX, build_gui_layout, create_gui_state
from ui.visual_checks import assert_visual_invariants, evaluate_visual_invariants


def _noop(*_args, **_kwargs) -> None:
    return None


def test_war_room_visual_invariants_hold_with_diagnostics_closed() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    invariants = assert_visual_invariants(layout)

    assert invariants["layout_expands"] == [LEFT_COLUMN_FLEX, CENTER_COLUMN_FLEX, RIGHT_COLUMN_FLEX]
    assert invariants["proposal_height_fixed"] is True


def test_diagnostics_drawer_open_does_not_mutate_layout_proportions() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    state.diagnostics_drawer_open = True
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    invariants = evaluate_visual_invariants(layout)

    assert invariants["layout_proportions_25_54_21"] is True
    assert invariants["diagnostics_overlay_not_layout_mutation"] is True


if __name__ == "__main__":
    test_war_room_visual_invariants_hold_with_diagnostics_closed()
    test_diagnostics_drawer_open_does_not_mutate_layout_proportions()
    print("test_gui_visual_invariants PASS")
