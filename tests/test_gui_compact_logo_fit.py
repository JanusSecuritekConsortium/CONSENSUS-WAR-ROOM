from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.header import (
    GUI_LOGO_BOX_HEIGHT,
    compact_logo_text,
    header_logo_layout,
    logo_text_control_from_box,
    supersampled_logo_metrics,
    theme_logo_layout_mode,
)
from ui.flet_app import build_gui_layout, create_gui_state
from ui.themes.catalog import THEMES


def _noop(*_args, **_kwargs) -> None:
    return None


def test_dedicated_compact_logo_line_counts_fit_header_height() -> None:
    for theme_key in ("eva", "nerv", "wh40k", "helldivers", "arasaka", "military", "janus"):
        lines = compact_logo_text(THEMES[theme_key]).splitlines()
        logo_layout = header_logo_layout(THEMES[theme_key])
        budget = logo_layout.logo_box_height or GUI_LOGO_BOX_HEIGHT

        assert 1 <= len(lines)
        if theme_logo_layout_mode(THEMES[theme_key])["mode"] == "ascii_grid_vector":
            assert len(lines) == 18
            assert max(len(line) for line in lines) == 39
            continue
        if theme_logo_layout_mode(THEMES[theme_key])["mode"] in {"supersampled_square", "supersampled_rect", "supersampled_banner"}:
            cell_width = int(logo_layout.logo_box_width or GUI_LOGO_BOX_HEIGHT)
            cell_height = int(logo_layout.logo_box_height or GUI_LOGO_BOX_HEIGHT)
            metrics = supersampled_logo_metrics(
                compact_logo_text(THEMES[theme_key]),
                base_font_size=int(logo_layout.logo_font_size),
                cell_width=cell_width,
                cell_height=cell_height,
                line_height_factor=logo_layout.logo_line_height,
            )
            assert metrics.fit_scale < 1.0
            assert metrics.visible_bottom <= cell_height - 6
            continue
        assert len(lines) * logo_layout.logo_font_size <= budget


def test_compact_logo_widths_fit_declared_header_constraints() -> None:
    for theme_key in ("eva", "nerv", "wh40k", "helldivers", "arasaka", "military", "janus"):
        state = create_gui_state(theme_key, RuntimeConfig(theme=theme_key, backend="mock"))
        layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
        logo_box = layout.content.controls[0].content.controls[0]
        mode = theme_logo_layout_mode(THEMES[theme_key])["mode"]
        if mode == "ascii_grid_vector":
            logo_text = logo_box.content.controls[0].data["source_text"]
        else:
            logo_text = logo_text_control_from_box(logo_box).value
        longest = max(len(line) for line in logo_text.splitlines())

        if mode == "percentage":
            assert logo_box.width is None
            assert logo_box.expand is not None
        elif mode in {"square", "supersampled_square"}:
            assert logo_box.width == GUI_LOGO_BOX_HEIGHT
            assert logo_box.height == GUI_LOGO_BOX_HEIGHT
            assert logo_box.expand is None
        elif mode in {"supersampled_rect", "supersampled_banner", "ascii_grid_vector"}:
            logo_layout = header_logo_layout(THEMES[theme_key])
            assert logo_box.width == logo_layout.logo_box_width
            assert logo_box.height == (logo_layout.logo_box_height or GUI_LOGO_BOX_HEIGHT)
            assert logo_box.expand is None
        elif mode == "historical":
            assert logo_box.width == header_logo_layout(THEMES[theme_key]).logo_box_width
            assert logo_box.expand is None
        assert longest <= 130
        expected_height = (
            (header_logo_layout(THEMES[theme_key]).logo_box_height or GUI_LOGO_BOX_HEIGHT)
            if mode in {"supersampled_rect", "supersampled_banner", "ascii_grid_vector"}
            else GUI_LOGO_BOX_HEIGHT
        )
        assert logo_box.height == expected_height
        assert logo_box.clip_behavior is not None
        assert logo_box.content.scroll is not None or header_logo_layout(THEMES[theme_key]).logo_box_scroll_enabled is False


if __name__ == "__main__":
    test_dedicated_compact_logo_line_counts_fit_header_height()
    test_compact_logo_widths_fit_declared_header_constraints()
    print("test_gui_compact_logo_fit PASS")
