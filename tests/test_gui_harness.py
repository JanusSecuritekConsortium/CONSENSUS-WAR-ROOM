from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import body_expand_contract, build_layout_for, header_logo_control_for, make_gui_state
from ui.components.header import LOGO_FONT_FAMILY, compact_logo_text


def test_gui_harness_builds_state_without_live_refresh() -> None:
    state = make_gui_state("ARASAKA", window_mode="fullscreen")

    assert state.theme_key == "arasaka"
    assert state.config.backend == "mock"
    assert state.window_mode == "fullscreen"
    assert state.provider_status["status"] == "ready"
    assert state.telemetry_snapshot["source"] == "test-harness"


def test_gui_harness_preserves_layout_contract() -> None:
    layout = build_layout_for("HELLDIVERS")

    assert body_expand_contract(layout) == [2, 6, 2]
    assert hasattr(layout, "diagnostics_drawer")
    assert hasattr(layout, "command_palette")


def test_gui_harness_reads_compact_logo_control() -> None:
    state = make_gui_state("WH40K")
    logo = header_logo_control_for("WH40K")

    assert logo.value == compact_logo_text(state.theme)
    assert logo.font_family == LOGO_FONT_FAMILY
    assert logo._Control__attrs["nowrap"][0] is True


if __name__ == "__main__":
    test_gui_harness_builds_state_without_live_refresh()
    test_gui_harness_preserves_layout_contract()
    test_gui_harness_reads_compact_logo_control()
    print("test_gui_harness PASS")
