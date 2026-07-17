from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS


def test_active_gui_logos_do_not_contain_mojibake_or_replacement_chars() -> None:
    bad_tokens = ("â", "�", "\ufffd")
    for asset in THEME_GRAPHIC_ASSETS.values():
        logo = read_normalized_logo(asset.logo_path)

        assert not any(token in logo.text for token in bad_tokens), asset.theme_key


def test_active_gui_logos_are_not_miniature_placeholders_and_are_bounded() -> None:
    for asset in THEME_GRAPHIC_ASSETS.values():
        logo = read_normalized_logo(asset.logo_path)

        assert 0 < logo.height <= asset.expected_max_lines, asset.theme_key
        assert 0 < logo.width <= asset.max_width, asset.theme_key
        assert "E X C O M M   W A R   R O O M   T R I B U N A L" not in logo.text
        assert "A R A S A K A   E X E C U T I V E" not in logo.text


def test_canonical_arasaka_and_military_logo_tokens_are_present() -> None:
    arasaka = read_normalized_logo(THEME_GRAPHIC_ASSETS["arasaka"].logo_path).text
    military = read_normalized_logo(THEME_GRAPHIC_ASSETS["military"].logo_path).text

    assert "sdmNNNs" in arasaka
    assert "mNNNNNNNNNNm" in arasaka
    assert "---×÷÷×----" in military
    assert "×÷÷÷÷÷÷÷÷×" in military
    assert "â" not in military


if __name__ == "__main__":
    test_active_gui_logos_do_not_contain_mojibake_or_replacement_chars()
    test_active_gui_logos_are_not_miniature_placeholders_and_are_bounded()
    test_canonical_arasaka_and_military_logo_tokens_are_present()
    print("test_no_scrambled_ascii_logos PASS")
