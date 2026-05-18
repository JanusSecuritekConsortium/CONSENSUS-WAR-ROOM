from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.runtime import RuntimeConfig
from ui.components.header import GUI_COMPACT_LOGO_FILES, compact_logo_text
from ui.flet_app import build_gui_layout, create_gui_state
from ui.themes.catalog import THEMES, resolve_theme_key


def _noop(*_args, **_kwargs) -> None:
    return None


def _header_logo_for(alias: str) -> str:
    state = create_gui_state(alias, RuntimeConfig(theme=alias, backend="mock"))
    layout = build_gui_layout(state, _noop, _noop, _noop, _noop, _noop)
    return layout.content.controls[0].content.controls[0].content.value


def test_eva_aliases_use_eva_compact_logo() -> None:
    expected = GUI_COMPACT_LOGO_FILES["eva"].read_text(encoding="utf-8").rstrip("\n")

    for alias in ("EVA", "NERV", "MAGI"):
        resolved = resolve_theme_key(alias)
        assert compact_logo_text(THEMES[resolved]) == expected
        assert _header_logo_for(alias) == expected


def test_wh40k_aliases_use_cogitator_compact_logo() -> None:
    expected = GUI_COMPACT_LOGO_FILES["wh40k"].read_text(encoding="utf-8").rstrip("\n")

    for alias in ("WH40K", "WARHAMMER", "COGITATOR"):
        resolved = resolve_theme_key(alias)
        assert compact_logo_text(THEMES[resolved]) == expected
        assert _header_logo_for(alias) == expected


def test_helldivers_aliases_use_managed_democracy_compact_logo() -> None:
    expected = GUI_COMPACT_LOGO_FILES["helldivers"].read_text(encoding="utf-8").rstrip("\n")

    for alias in ("HELLDIVERS", "SUPER_EARTH", "DEMOCRACY"):
        resolved = resolve_theme_key(alias)
        assert compact_logo_text(THEMES[resolved]) == expected
        assert _header_logo_for(alias) == expected


if __name__ == "__main__":
    test_eva_aliases_use_eva_compact_logo()
    test_wh40k_aliases_use_cogitator_compact_logo()
    test_helldivers_aliases_use_managed_democracy_compact_logo()
    print("test_gui_compact_logo_aliases PASS")
