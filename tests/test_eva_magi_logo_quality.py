from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_eva_magi_logo_is_blocky_cube_style() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["eva"].logo_path)

    assert "XXXXXXXX" in logo.text
    assert "MAGI CUBE ARRAY" in logo.text
    assert "CASPER" in logo.text
    assert "BALTHASAR" in logo.text
    assert "MELCHIOR" in logo.text
    assert logo.height >= 9


if __name__ == "__main__":
    test_eva_magi_logo_is_blocky_cube_style()
    print("test_eva_magi_logo_quality PASS")
