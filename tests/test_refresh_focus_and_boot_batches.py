from types import SimpleNamespace
import random

import flet as ft

from config.runtime import RuntimeConfig
from config.nodes import DEFAULT_NODES
from ui import flet_app as gui
from tools import eva_boot_dummy as boot


def test_live_refresh_keeps_editor_footer_and_overlays_mounted(monkeypatch):
    state = gui.GuiState(theme_key="arasaka", config=RuntimeConfig(backend="mock"), nodes=DEFAULT_NODES)
    noop = lambda *args: None
    # Avoid unrelated disk-backed operator viewers in this focused UI test.
    for name in ("build_diagnostics_drawer", "build_command_palette", "build_decision_trace_viewer",
                 "build_proposal_history_viewer", "build_visual_review_status_viewer",
                 "build_telemetry_snapshot_viewer", "build_simulation_viewer",
                 "build_simulation_create_overlay", "build_branch_tree_viewer"):
        monkeypatch.setattr(gui, name, lambda *args, **kwargs: ft.Container())
    layout = gui.build_gui_layout(state, noop, noop, noop, noop, noop)
    editor_region = layout.content.controls[1].content.controls[1].content.controls[0]
    footer = layout.content.controls[2]
    editor = next(c for c in editor_region.content.content.controls if isinstance(c, ft.TextField))
    editor.value = "An unfinished query"
    overlay = ft.TextField(value="Open overlay draft")
    updates = []
    page = SimpleNamespace(controls=[layout], overlay=[overlay], update=lambda *controls: updates.append(controls))
    old_log_content = state.live_panels["build_log_panel"][0].content
    for tick in range(3):
        state.timeline_events.append(f"tick {tick}")
        gui._refresh_live_page(page, state)
    assert page.controls == [layout]
    assert layout.content.controls[2] is footer
    assert layout.content.controls[1].content.controls[1].content.controls[0] is editor_region
    assert editor.value == "An unfinished query"
    assert page.overlay == [overlay]
    assert state.live_panels["build_log_panel"][0].content is not old_log_content
    assert all(len(update) == 5 for update in updates)
    assert all(editor_region not in update and footer not in update for update in updates)


def test_boot_prints_random_complete_line_batches(monkeypatch):
    rng_factory = random.Random
    patterns = []
    lines = [f"POST {i} [OK]" for i in range(40)]
    for seed in (17, 29):
        monkeypatch.setattr(boot.random, "Random", lambda: rng_factory(seed))
        written, batches, pauses = [], [], []
        monkeypatch.setattr(boot, "_write_styled_line", lambda line, *args: written.append(line))
        def wait(delay, controls):
            batches.append(len(written))
            pauses.append(delay)
            return True
        monkeypatch.setattr(boot, "_wait_with_controls", wait)
        monkeypatch.setattr(boot, "_type_styled_line", lambda *args: (_ for _ in ()).throw(AssertionError("typing")))
        assert boot._type_styled_lines(lines, .001, .01, boot.EvaPalette())
        assert written == lines
        sizes = [end-start for start, end in zip([0]+batches, batches)]
        assert all(3 <= size <= 8 for size in sizes[:-1])
        assert set(pauses) <= {0.5, 1.0, 2.0}
        assert len(set(pauses)) > 1
        patterns.append(sizes)
    assert patterns[0] != patterns[1]


def test_boot_skip_stops_before_emitting_a_batch(monkeypatch):
    monkeypatch.setattr(boot, "_poll_controls", lambda controls: None)
    monkeypatch.setattr(boot, "_write_styled_line", lambda *args: (_ for _ in ()).throw(AssertionError("output after skip")))
    controls = boot.PreviewControls()
    controls.skip = True
    assert not boot._type_styled_lines(["POST"], .001, .01, boot.EvaPalette(), controls=controls)
