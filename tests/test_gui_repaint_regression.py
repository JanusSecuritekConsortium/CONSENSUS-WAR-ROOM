from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.flet_app import _render_page, create_gui_state


class FakePage:
    def __init__(self) -> None:
        self.controls = []
        self.updated = 0
        self.title = ""
        self.bgcolor = ""
        self.theme = None
        self.scroll = "auto"
        self.padding = 10
        self.spacing = 10

    def add(self, control) -> None:
        self.controls.append(control)

    def update(self) -> None:
        self.updated += 1

    def close(self) -> None:
        return None


def test_render_page_skips_reentrant_full_page_repaint() -> None:
    state = create_gui_state("EVA", RuntimeConfig(theme="eva", backend="mock"))
    page = FakePage()
    state.render_in_progress = True

    _render_page(page, state)  # type: ignore[arg-type]

    assert page.controls == []
    assert page.updated == 0
    assert state.render_in_progress is True


if __name__ == "__main__":
    test_render_page_skips_reentrant_full_page_repaint()
    print("test_gui_repaint_regression PASS")
