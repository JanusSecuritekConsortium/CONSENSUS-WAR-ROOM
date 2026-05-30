from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui.flet_app as flet_app
from tests.helpers.gui_harness import make_gui_state


def test_diagnostics_toggle_does_not_build_fresh_runtime_snapshot() -> None:
    state = make_gui_state("arasaka")
    original_snapshot = flet_app.build_runtime_snapshot
    try:
        flet_app.build_runtime_snapshot = lambda: (_ for _ in ()).throw(AssertionError("fresh snapshot called"))

        opened = flet_app.set_diagnostics_drawer_open(state, True)
        closed = flet_app.set_diagnostics_drawer_open(state, False)

        assert opened is True
        assert closed is False
        assert state.runtime_snapshot_cache
    finally:
        flet_app.build_runtime_snapshot = original_snapshot


if __name__ == "__main__":
    test_diagnostics_toggle_does_not_build_fresh_runtime_snapshot()
    print("test_diagnostics_button_nonblocking PASS")
