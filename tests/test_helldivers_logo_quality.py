from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_helldivers_logo_is_sparse_readable_ascii_emblem() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["helldivers"].logo_path)
    text = logo.text

    assert "SUPER EARTH COMMAND" in text
    assert "MANAGED DEMOCRACY ONLINE" in text
    assert "LIBERTY WINGS" in text
    assert "@@@@" not in text
    assert 8 <= logo.height <= 12
    assert logo.width <= 70


if __name__ == "__main__":
    test_helldivers_logo_is_sparse_readable_ascii_emblem()
    print("test_helldivers_logo_quality PASS")
