from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_eva_magi_logo_uses_nerv_reference_geometry() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["eva"].logo_path)

    assert "###########################" in logo.text
    assert "################################" in logo.text
    assert "NERV GEOMETRIC MAGI MARK" not in logo.text
    assert "CASPER" not in logo.text
    assert "BALTHASAR" not in logo.text
    assert "MELCHIOR" not in logo.text
    assert logo.height == 56
    assert logo.width == 88


if __name__ == "__main__":
    test_eva_magi_logo_uses_nerv_reference_geometry()
    print("test_eva_magi_logo_quality PASS")
