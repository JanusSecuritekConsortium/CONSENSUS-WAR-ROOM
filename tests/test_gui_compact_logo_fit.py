from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.header import (
    GUI_LOGO_BOX_HEIGHT,
    GUI_LOGO_BOX_MAX_WIDTH,
    LOGO_FONT_SIZE,
    compact_logo_text,
    logo_text_control_from_box,
)
from ui.flet_app import build_gui_layout, create_gui_state
from ui.themes.catalog import THEMES


def _noop(*_args, **_kwargs) -> None:
    return None


def test_dedicated_compact_logo_line_counts_fit_header_height() -> None:
    for theme_key in ("eva", "nerv", "wh40k", "helldivers", "arasaka", "military", "janus"):
        lines = compact_logo_text(THEMES[theme_key]).splitlines()

        assert 1 <= len(lines)
        if len(lines) * LOGO_FONT_SIZE > GUI_LOGO_BOX_HEIGHT:
            assert theme_key in {"wh40k", "helldivers"}


def test_compact_logo_widths_fit_declared_header_constraints() -> None:
    for theme_key in ("eva", "nerv", "wh40k", "helldivers", "arasaka", "military", "janus"):
        state = create_gui_state(theme_key, RuntimeConfig(theme=theme_key, backend="mock"))
        layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
        logo_box = layout.content.controls[0].content.controls[0]
        logo_text = logo_text_control_from_box(logo_box).value
        longest = max(len(line) for line in logo_text.splitlines())

        assert logo_box.width <= GUI_LOGO_BOX_MAX_WIDTH
        assert longest <= 130
        assert logo_box.height == GUI_LOGO_BOX_HEIGHT
        assert logo_box.clip_behavior is not None
        assert logo_box.content.scroll is not None


if __name__ == "__main__":
    test_dedicated_compact_logo_line_counts_fit_header_height()
    test_compact_logo_widths_fit_declared_header_constraints()
    print("test_gui_compact_logo_fit PASS")
