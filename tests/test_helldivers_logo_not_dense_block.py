from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_helldivers_logo_is_not_dense_at_block() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["helldivers"].logo_path)

    assert "@" not in logo.text
    assert max(line.count("=") for line in logo.lines) <= 24
    assert logo.width <= 70


if __name__ == "__main__":
    test_helldivers_logo_is_not_dense_at_block()
    print("test_helldivers_logo_not_dense_block PASS")
