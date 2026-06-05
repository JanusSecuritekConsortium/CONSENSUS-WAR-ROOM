from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS, get_theme_graphic_asset, validate_graphic_registry


def test_logo_registry_covers_active_gui_themes() -> None:
    for theme_key in ("eva", "nerv", "wh40k", "helldivers", "arasaka", "janus", "military"):
        asset = get_theme_graphic_asset(theme_key)

        assert asset.theme_key == theme_key
        assert asset.logo_path.exists()
        assert asset.boot_profile


def test_logo_registry_validation_is_clean() -> None:
    assert validate_graphic_registry() == []


def test_logo_registry_reports_exact_theme_for_missing_key() -> None:
    try:
        get_theme_graphic_asset("missing")
    except KeyError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("missing theme registry lookup did not fail")


def test_military_registry_uses_gui_header_logo_source() -> None:
    asset = get_theme_graphic_asset("military")
    gui_header = ROOT / "static" / "logos" / "gui" / "military_header.txt"
    boot_logo = ROOT / "static" / "logos" / "consensus_logo.txt"

    assert asset.logo_path == gui_header
    assert read_normalized_logo(asset.logo_path).text == read_normalized_logo(gui_header).text
    assert asset.logo_path != boot_logo
    assert "███████╗██╗  ██╗" in read_normalized_logo(asset.logo_path).text
    assert "CONSENSUS WAR ROOM" in read_normalized_logo(asset.logo_path).text


if __name__ == "__main__":
    test_logo_registry_covers_active_gui_themes()
    test_logo_registry_validation_is_clean()
    test_logo_registry_reports_exact_theme_for_missing_key()
    test_military_registry_uses_gui_header_logo_source()
    print("test_logo_registry PASS")
