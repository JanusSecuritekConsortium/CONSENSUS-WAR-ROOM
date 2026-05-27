from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import normalize_logo_text


def test_logo_normalizer_strips_bom_and_normalizes_line_endings() -> None:
    logo = normalize_logo_text("\ufeff  AB\r\n CD \r\n")

    assert logo.had_bom is True
    assert logo.lines == ("  AB", " CD")
    assert logo.width == 4
    assert logo.height == 2
    assert logo.text == "  AB\n CD"


def test_logo_normalizer_preserves_leading_spaces_and_can_pad_lines() -> None:
    logo = normalize_logo_text("  A\n B", pad_lines=True)

    assert logo.lines == ("  A", " B ")
    assert logo.width == 3
    assert logo.text == "  A\n B "


if __name__ == "__main__":
    test_logo_normalizer_strips_bom_and_normalizes_line_endings()
    test_logo_normalizer_preserves_leading_spaces_and_can_pad_lines()
    print("test_logo_normalizer PASS")
