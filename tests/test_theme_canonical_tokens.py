from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS, validate_graphic_registry


def test_all_theme_assets_include_canonical_tokens() -> None:
    assert validate_graphic_registry() == []
    for theme_key, asset in THEME_GRAPHIC_ASSETS.items():
        logo = read_normalized_logo(asset.logo_path).text
        for token in asset.canonical_tokens:
            assert token in logo, f"{theme_key} missing {token!r}"


def test_military_gui_logo_is_separate_from_boot_consensus_source() -> None:
    canonical = ROOT / "static" / "logos" / "consensus_logo.txt"
    gui_header = ROOT / "static" / "logos" / "gui" / "military_header.txt"
    military = THEME_GRAPHIC_ASSETS["military"]

    assert military.logo_path == gui_header
    assert read_normalized_logo(military.logo_path).text == read_normalized_logo(gui_header).text
    assert military.logo_path != canonical
    assert "CONSENSUS WAR ROOM" in read_normalized_logo(military.logo_path).text


def test_wh40k_and_helldivers_headers_are_full_identity_banners() -> None:
    wh40k = read_normalized_logo(THEME_GRAPHIC_ASSETS["wh40k"].logo_path)
    helldivers = read_normalized_logo(THEME_GRAPHIC_ASSETS["helldivers"].logo_path)

    for token in ("###########################", "####     ########    ####", "#############"):
        assert token in helldivers.text
    for token in ("@@@@@@@@", "@@@@@@@#", "#@@"):
        assert token in wh40k.text
    assert 50 <= wh40k.height <= 56
    assert wh40k.width >= 80
    assert helldivers.height == 19
    assert helldivers.width >= 80


if __name__ == "__main__":
    test_all_theme_assets_include_canonical_tokens()
    test_military_gui_logo_is_separate_from_boot_consensus_source()
    test_wh40k_and_helldivers_headers_are_full_identity_banners()
    print("test_theme_canonical_tokens PASS")
