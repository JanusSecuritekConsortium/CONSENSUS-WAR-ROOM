from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.components.header import GUI_COMPACT_LOGO_FILES, compact_logo_text, has_dedicated_gui_compact_logo
from ui.assets.logo_normalizer import read_normalized_logo
from ui.themes.catalog import THEMES


DEDICATED_THEME_KEYS = ("eva", "nerv", "wh40k", "helldivers", "arasaka", "military", "janus")


def test_supplied_gui_compact_logo_assets_exist() -> None:
    for theme_key in DEDICATED_THEME_KEYS:
        path = GUI_COMPACT_LOGO_FILES[theme_key]
        assert path.exists(), theme_key
        assert path.read_text(encoding="utf-8").strip(), theme_key


def test_supplied_gui_compact_logos_are_selected() -> None:
    for theme_key in DEDICATED_THEME_KEYS:
        theme = THEMES[theme_key]
        if theme_key in {"eva", "nerv", "helldivers"}:
            expected = GUI_COMPACT_LOGO_FILES[theme_key].read_bytes().decode("utf-8")
        else:
            expected = read_normalized_logo(GUI_COMPACT_LOGO_FILES[theme_key]).text

        assert has_dedicated_gui_compact_logo(theme)
        assert compact_logo_text(theme) == expected


def test_new_compact_logo_identity_text_is_present() -> None:
    assert "###########################" in compact_logo_text(THEMES["eva"])
    assert "@@@@@@@@" in compact_logo_text(THEMES["wh40k"])
    assert "@@@@@@@#" in compact_logo_text(THEMES["wh40k"])
    assert "####     ########    ####" in compact_logo_text(THEMES["helldivers"])


if __name__ == "__main__":
    test_supplied_gui_compact_logo_assets_exist()
    test_supplied_gui_compact_logos_are_selected()
    test_new_compact_logo_identity_text_is_present()
    print("test_gui_compact_logos PASS")
