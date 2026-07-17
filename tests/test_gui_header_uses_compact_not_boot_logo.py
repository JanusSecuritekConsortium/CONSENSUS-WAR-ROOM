from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for, header_logo_control_for, make_gui_state
from ui.components.header import compact_logo_text, header_logo_text, theme_logo_layout_mode


def _header_logo_for(theme_key: str) -> str:
    state = make_gui_state(theme_key)
    if theme_logo_layout_mode(state.theme)["mode"] == "ascii_grid_vector":
        layout = build_layout_for(state.theme_key)
        return layout.content.controls[0].content.controls[0].content.controls[0].data["source_text"]
    return header_logo_control_for(theme_key).value


def test_gui_header_uses_dedicated_compact_logo_not_full_boot_logo() -> None:
    for theme_key in ("EVA", "NERV", "WH40K", "HELLDIVERS", "ARASAKA", "MILITARY", "JANUS"):
        state = make_gui_state(theme_key)
        header_logo = _header_logo_for(theme_key)

        assert header_logo == header_logo_text(state.theme)
        if state.theme_key != "MILITARY":
            assert header_logo != state.theme.logo.rstrip("\n")


def test_arasaka_header_uses_wordmark_without_top_emblem() -> None:
    logo = _header_logo_for("ARASAKA")

    assert "sdmNNNs" in logo
    assert "mNNNNNNNNNNm" in logo
    assert ".--:////:--." not in logo


def test_boot_logo_assets_remain_full_theme_logos() -> None:
    for theme_key in ("EVA", "WH40K", "HELLDIVERS"):
        state = make_gui_state(theme_key)
        header_logo = _header_logo_for(theme_key)

        assert header_logo != state.theme.logo.rstrip("\n")
        assert "static\\logos\\gui" not in state.theme.logo_path


if __name__ == "__main__":
    test_gui_header_uses_dedicated_compact_logo_not_full_boot_logo()
    test_arasaka_header_uses_wordmark_without_top_emblem()
    test_boot_logo_assets_remain_full_theme_logos()
    print("test_gui_header_uses_compact_not_boot_logo PASS")
