from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_eva_logo_has_rectangular_render_footprint() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["eva"].logo_path, pad_lines=True)
    widths = {len(line) for line in logo.lines}

    assert len(widths) == 1
    assert 50 <= logo.width <= 70


if __name__ == "__main__":
    test_eva_logo_has_rectangular_render_footprint()
    print("test_eva_logo_rectangular_alignment PASS")
