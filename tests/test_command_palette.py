from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui import flet_app as gui
from ui.flet_app import (
    COMMAND_PALETTE_ACTIONS,
    build_command_palette,
    command_palette_geometry,
    command_palette_scroll_offset,
    create_gui_state,
    execute_command_palette_action,
    move_command_palette_selection,
    select_command_palette_tile,
)


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "text") and isinstance(control.text, str):
        values.append(control.text)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def _state():
    return create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))


def _open_palette(width: int = 1280, height: int = 720):
    """Render the real page with the palette open, on a fake window."""
    from tests.helpers.gui_harness import make_gui_state
    from tests.test_diagnostics_overlay_reentrant_guard import FakePage

    state = make_gui_state("janus")
    page = FakePage()
    page.width, page.height = width, height
    page.on_resized = None  # the app only hooks resizing on pages that support it
    gui._render_page(page, state)
    page.on_keyboard_event(SimpleNamespace(key="K", ctrl=True))
    assert state.command_palette_open
    return page, state


def _backdrop(page):
    return next(c for c in page.overlay if c.data == "command_palette")


def _selected(state) -> list[int]:
    return [tile.data["index"] for tile in state.command_palette_view.tiles if tile.data["selected"]]


def test_command_palette_lists_operator_actions() -> None:
    palette = build_command_palette(_state())
    text = "\n".join(_flatten_text(palette))

    assert "COMMAND PALETTE" in text
    for action in COMMAND_PALETTE_ACTIONS:
        assert action in text


def test_command_palette_state_actions() -> None:
    state = _state()

    execute_command_palette_action(state, "Open Diagnostics")
    assert state.diagnostics_drawer_open is True

    execute_command_palette_action(state, "Open Decision Trace Viewer")
    assert state.trace_viewer_open is True

    original_theme = state.theme_key
    execute_command_palette_action(state, "Toggle Theme")
    assert state.theme_key != original_theme


def test_command_palette_is_a_square_sized_from_the_window() -> None:
    for width, height in ((1920, 1080), (1280, 720), (900, 1400), (640, 420), (320, 300)):
        palette = build_command_palette(_state(), page_width=width, page_height=height)
        assert palette.width == palette.height
        assert palette.width <= width - 16
        assert palette.height <= height - gui.FOOTER_HEIGHT - 16
    large = command_palette_geometry(1920, 1080)
    small = command_palette_geometry(640, 420)
    assert large["side"] > small["side"]
    assert large["columns"] > small["columns"] >= 1


def test_command_palette_is_a_wrapping_grid_that_scrolls_inside_the_square() -> None:
    palette = build_command_palette(_state(), page_width=1280, page_height=720)
    column = palette.content
    grid = palette.grid
    assert isinstance(grid, ft.GridView) and grid in column.controls
    assert grid.expand is True  # the grid takes the leftover room and scrolls; the square keeps its size
    assert grid.runs_count == palette.geometry["columns"] > 1
    assert [tile.data["action"] for tile in grid.controls] == list(COMMAND_PALETTE_ACTIONS)
    assert all(isinstance(tile, ft.Container) for tile in grid.controls)


def test_new_command_needs_no_layout_change(monkeypatch) -> None:
    extra = tuple(f"Future Command {number}" for number in range(40))
    monkeypatch.setattr(gui, "COMMAND_PALETTE_ACTIONS", COMMAND_PALETTE_ACTIONS + extra)
    before = command_palette_geometry(1280, 720)
    palette = build_command_palette(_state(), page_width=1280, page_height=720)
    assert len(palette.grid.controls) == len(COMMAND_PALETTE_ACTIONS) + 40
    assert palette.width == palette.height == before["side"]
    assert "Future Command 39" in "\n".join(_flatten_text(palette))


def test_arrow_keys_move_across_the_grid_in_both_directions() -> None:
    columns, count = 3, 8  # rows: 0 1 2 / 3 4 5 / 6 7
    move = lambda index, key: move_command_palette_selection(index, key, columns, count)
    assert move(0, "Arrow Right") == 1
    assert move(1, "Arrow Left") == 0
    assert move(0, "Arrow Left") == 0
    assert move(2, "Arrow Right") == 3  # end of a row continues on the next one
    assert move(1, "Arrow Down") == 4
    assert move(4, "Arrow Up") == 1
    assert move(1, "Arrow Up") == 1
    assert move(5, "Arrow Down") == 7  # short last row: land on its last tile
    assert move(7, "Arrow Down") == 7
    assert move(7, "Arrow Right") == 7
    assert move(4, "Home") == 0 and move(4, "End") == 7
    assert move(4, "A") == 4
    assert move_command_palette_selection(0, "Arrow Down", 3, 0) == 0


def test_selection_scrolls_only_as_far_as_needed() -> None:
    # 64px tiles with an 8px gap, three columns, a 200px tall grid.
    assert command_palette_scroll_offset(0, 3, 0, 200) == 0
    assert command_palette_scroll_offset(6, 3, 0, 200) == 8  # third row ends at 208
    assert command_palette_scroll_offset(12, 3, 8, 200) == 152
    assert command_palette_scroll_offset(3, 3, 152, 200) == 72  # back up: row top
    assert command_palette_scroll_offset(6, 3, 72, 200) == 72  # already visible


def test_exactly_one_tile_is_highlighted_and_it_follows_the_selection() -> None:
    state = _state()
    palette = build_command_palette(state, page_width=1280, page_height=720)
    assert [t.data["index"] for t in palette.tiles if t.data["selected"]] == [0]
    changed = select_command_palette_tile(palette, 4, state.theme)
    assert changed == [palette.tiles[0], palette.tiles[4]]
    assert [t.data["index"] for t in palette.tiles if t.data["selected"]] == [4]
    assert palette.tiles[4].border != palette.tiles[0].border
    assert select_command_palette_tile(palette, 4, state.theme) == []


def test_ctrl_k_opens_a_centred_square_above_the_footer() -> None:
    page, state = _open_palette(1280, 720)
    backdrop = _backdrop(page)
    panel = backdrop.content
    assert backdrop.alignment == ft.alignment.center
    assert (backdrop.top, backdrop.left, backdrop.right) == (0, 0, 0)
    assert backdrop.bottom == gui.FOOTER_HEIGHT
    assert panel is state.command_palette_view
    assert panel.width == panel.height == command_palette_geometry(1280, 720)["side"]


def test_keyboard_moves_runs_and_closes(monkeypatch) -> None:
    page, state = _open_palette(1280, 720)
    columns = state.command_palette_view.geometry["columns"]
    press = lambda key: page.on_keyboard_event(SimpleNamespace(key=key))

    press("Arrow Right")
    assert state.command_palette_index == 1 and _selected(state) == [1]
    press("Arrow Down")
    assert state.command_palette_index == 1 + columns and _selected(state) == [1 + columns]
    press("Arrow Left")
    press("Arrow Up")
    assert state.command_palette_index == 0 and _selected(state) == [0]

    ran = []
    monkeypatch.setattr(gui, "execute_command_palette_action", lambda state, action: ran.append(action))
    press("Arrow Right")
    press("Enter")
    assert ran == [COMMAND_PALETTE_ACTIONS[1]]
    assert not state.command_palette_open
    assert not any(c.data == "command_palette" for c in page.overlay)

    # Reopening starts again on the first tile; Esc closes without running anything.
    page.on_keyboard_event(SimpleNamespace(key="K", ctrl=True))
    assert state.command_palette_open and state.command_palette_index == 0
    press("Escape")
    assert not state.command_palette_open and ran == [COMMAND_PALETTE_ACTIONS[1]]
    assert not any(c.data == "command_palette" for c in page.overlay)


def test_keys_do_nothing_while_the_palette_is_closed(monkeypatch) -> None:
    page, state = _open_palette()
    page.on_keyboard_event(SimpleNamespace(key="Escape"))
    ran = []
    monkeypatch.setattr(gui, "execute_command_palette_action", lambda state, action: ran.append(action))
    for key in ("Enter", "Arrow Down", "Escape"):
        page.on_keyboard_event(SimpleNamespace(key=key))
    assert ran == [] and not state.command_palette_open and state.command_palette_index == 0


def test_mouse_click_runs_a_tile_and_clicking_outside_closes(monkeypatch) -> None:
    page, state = _open_palette()
    ran = []
    monkeypatch.setattr(gui, "execute_command_palette_action", lambda state, action: ran.append(action))
    panel = state.command_palette_view
    assert panel.on_click is not None  # the panel swallows clicks, so they do not reach the backdrop
    panel.on_click(None)
    assert state.command_palette_open and ran == []

    tile = next(t for t in panel.tiles if t.data["action"] == "Open Diagnostics")
    tile.on_click(None)
    assert ran == ["Open Diagnostics"] and not state.command_palette_open

    page.on_keyboard_event(SimpleNamespace(key="K", ctrl=True))
    assert state.command_palette_open
    _backdrop(page).on_click(None)
    assert not state.command_palette_open and ran == ["Open Diagnostics"]
    assert not any(c.data == "command_palette" for c in page.overlay)


def test_resizing_the_window_resizes_an_open_palette() -> None:
    page, state = _open_palette(1280, 720)
    before = state.command_palette_view.width
    page.width, page.height = 700, 460
    page.on_resized(None)
    after = state.command_palette_view
    assert after.width == after.height < before
    assert after.width == command_palette_geometry(700, 460)["side"]
