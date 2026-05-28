from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.components.header import compact_logo_text
from ui.themes.catalog import THEMES


def _has_trailing_spaces(text: str) -> bool:
    return any(line.endswith(" ") for line in text.splitlines())


def test_user_header_assets_preserve_trailing_and_leading_whitespace() -> None:
    for theme_key in ("eva", "helldivers"):
        raw_text = THEME_GRAPHIC_ASSETS[theme_key].logo_path.read_bytes().decode("utf-8")
        rendered_text = compact_logo_text(THEMES[theme_key])

        assert rendered_text == raw_text
        assert raw_text.startswith(" ")
        assert _has_trailing_spaces(raw_text)


if __name__ == "__main__":
    test_user_header_assets_preserve_trailing_and_leading_whitespace()
    print("test_logo_whitespace_preserved PASS")
