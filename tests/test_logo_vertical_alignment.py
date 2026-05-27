from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_logo_vertical_padding_fits_render_budget() -> None:
    for theme_key, asset in THEME_GRAPHIC_ASSETS.items():
        logo = read_normalized_logo(asset.logo_path)
        layout = asset.header_layout
        required = logo.height * layout.logo_font_size + layout.logo_top_padding + layout.logo_bottom_padding

        assert required <= 230 if theme_key == "wh40k" else required <= 142


if __name__ == "__main__":
    test_logo_vertical_padding_fits_render_budget()
    print("test_logo_vertical_alignment PASS")
