from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS, validate_theme_graphic_asset


def test_wh40k_header_asset_is_restored_v71013_gothic_asset() -> None:
    asset = THEME_GRAPHIC_ASSETS["wh40k"]
    logo = read_normalized_logo(asset.logo_path)

    assert validate_theme_graphic_asset(asset) == []
    assert 50 <= logo.height <= 60
    assert 80 <= logo.width <= 96
    for token in ("@@@@@@@@", "@@@@@@@#", "#@@"):
        assert token in logo.text


def test_wh40k_header_asset_rejects_v71014_compact_skull_replacement() -> None:
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["wh40k"].logo_path)

    assert logo.height > 30
    assert "COGITATOR" not in logo.text
    assert "ADEPTUS MECHANICUS :: IMPERIAL COGITATOR TRIBUNAL" not in logo.text


if __name__ == "__main__":
    test_wh40k_header_asset_is_restored_v71013_gothic_asset()
    test_wh40k_header_asset_rejects_v71014_compact_skull_replacement()
    print("test_wh40k_compact_logo_asset PASS")
