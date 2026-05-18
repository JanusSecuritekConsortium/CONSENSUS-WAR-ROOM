from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.header import compact_logo_text
from ui.flet_app import build_gui_layout, create_gui_state


def _noop(*_args, **_kwargs) -> None:
    return None


def _header_logo_for(theme_key: str) -> str:
    state = create_gui_state(theme_key, RuntimeConfig(theme=theme_key, backend="mock"))
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    return layout.content.controls[0].content.controls[0].content.value


def test_gui_header_uses_dedicated_compact_logo_not_full_boot_logo() -> None:
    for theme_key in ("EVA", "NERV", "WH40K", "HELLDIVERS", "ARASAKA", "MILITARY", "JANUS"):
        state = create_gui_state(theme_key, RuntimeConfig(theme=theme_key, backend="mock"))
        header_logo = _header_logo_for(theme_key)

        assert header_logo == compact_logo_text(state.theme)
        assert header_logo != state.theme.logo.rstrip("\n")


def test_arasaka_header_uses_wordmark_without_top_emblem() -> None:
    logo = _header_logo_for("ARASAKA")

    assert ".sdmNNNs-" in logo
    assert ".--:////:--." not in logo


def test_boot_logo_assets_remain_full_theme_logos() -> None:
    for theme_key in ("EVA", "WH40K", "HELLDIVERS"):
        state = create_gui_state(theme_key, RuntimeConfig(theme=theme_key, backend="mock"))
        header_logo = _header_logo_for(theme_key)

        assert header_logo != state.theme.logo.rstrip("\n")
        assert "static\\logos\\gui" not in state.theme.logo_path


if __name__ == "__main__":
    test_gui_header_uses_dedicated_compact_logo_not_full_boot_logo()
    test_arasaka_header_uses_wordmark_without_top_emblem()
    test_boot_logo_assets_remain_full_theme_logos()
    print("test_gui_header_uses_compact_not_boot_logo PASS")
