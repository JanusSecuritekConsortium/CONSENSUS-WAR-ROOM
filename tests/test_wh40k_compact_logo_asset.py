from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS, validate_theme_graphic_asset


def test_wh40k_header_asset_is_compact_and_canonical() -> None:
    asset = THEME_GRAPHIC_ASSETS["wh40k"]
    logo = read_normalized_logo(asset.logo_path)

    assert validate_theme_graphic_asset(asset) == []
    assert 12 <= logo.height <= 16
    assert 55 <= logo.width <= 96
    for token in ("@@@@@@@@", "@@@@@@@#", "#@@", "COGITATOR", "OMNISSIAH"):
        assert token in logo.text


def test_wh40k_header_asset_replaces_unreadably_tall_eagle() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["wh40k"].logo_path)

    assert logo.height < 30
    assert "ADEPTUS MECHANICUS :: IMPERIAL COGITATOR TRIBUNAL" not in logo.text


if __name__ == "__main__":
    test_wh40k_header_asset_is_compact_and_canonical()
    test_wh40k_header_asset_replaces_unreadably_tall_eagle()
    print("test_wh40k_compact_logo_asset PASS")
