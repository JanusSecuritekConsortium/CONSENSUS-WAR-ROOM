from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.registry import GUI_LOGO_ROOT, THEME_GRAPHIC_ASSETS, validate_gui_logo_path
from ui.components.header import logo_runtime_diagnostics


EXPECTED_EVA_GUI_HASH = "5c10f1a59339b6a788880c4187481c0d3290abddc1dff9da80389fa8684df476"
EXPECTED_WH40K_GUI_HASH = "dfe05107f652c009ef1c7a5efc6005adc82ceae42ff321870acdb67c21ec150c"
EVA_BOOT_HASH = "04786ec6cbfad90e20c91a4ff8e3de24ef056320734f4174add37631cf1069b8"
WH40K_BOOT_HASH = "c15e317b7230dcff6ba757a1426aeae2266da88a23c3f24c7c2da3ba9836d8e6"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_eva_and_wh40k_runtime_logo_paths_are_canonical_gui_files() -> None:
    expected = {
        "eva": (GUI_LOGO_ROOT / "eva_header.txt").resolve(),
        "wh40k": (GUI_LOGO_ROOT / "wh40k_header.txt").resolve(),
    }
    hashes = {"eva": EXPECTED_EVA_GUI_HASH, "wh40k": EXPECTED_WH40K_GUI_HASH}
    boot_hashes = {"eva": EVA_BOOT_HASH, "wh40k": WH40K_BOOT_HASH}

    for theme_key, expected_path in expected.items():
        path = THEME_GRAPHIC_ASSETS[theme_key].logo_path.resolve()

        validate_gui_logo_path(path)
        assert path == expected_path
        assert path.name == f"{theme_key}_header.txt"
        assert path.parent == GUI_LOGO_ROOT
        assert "future_implementations" not in str(path)
        assert "reports" not in str(path)
        assert "archive" not in str(path)
        assert _sha256(path) == hashes[theme_key]
        assert _sha256(path) != boot_hashes[theme_key]


def test_wh40k_positive_optical_offset_keeps_logo_contained() -> None:
    diagnostics = logo_runtime_diagnostics("wh40k", header_width=1920)
    left, right, top, bottom = diagnostics["clearances"]

    assert diagnostics["optical_offset_x"] == 6
    assert left >= 5
    assert right >= 5
    assert top >= 5
    assert bottom >= 5


def test_eva_gui_logo_bounds_are_contained_without_clipping() -> None:
    diagnostics = logo_runtime_diagnostics("eva", header_width=1920)
    left, right, top, bottom = diagnostics["clearances"]

    assert diagnostics["renderer_mode"] == "supersampled_rect"
    assert diagnostics["logo_region_width"] == 185
    assert diagnostics["logo_region_height"] == 168
    assert diagnostics["visible_artwork_width"] >= 172
    assert diagnostics["visible_artwork_height"] >= 148
    assert left >= 6
    assert right >= 6
    assert top >= 9
    assert bottom >= 9


def test_bundled_onefile_gui_logo_hashes_match_source_gui_hashes() -> None:
    exe_path = ROOT / "dist" / "CONSENSUS.exe"
    if not exe_path.exists():
        pytest.skip("CONSENSUS.exe has not been built yet")

    archive = CArchiveReader(str(exe_path))
    expected = {
        "static\\logos\\gui\\eva_header.txt": EXPECTED_EVA_GUI_HASH,
        "static\\logos\\gui\\wh40k_header.txt": EXPECTED_WH40K_GUI_HASH,
    }

    for archive_name, expected_hash in expected.items():
        payload = archive.extract(archive_name)
        assert hashlib.sha256(payload).hexdigest() == expected_hash


def test_no_png_gui_logo_assets_exist() -> None:
    assert not list(GUI_LOGO_ROOT.glob("*.png"))


if __name__ == "__main__":
    test_eva_and_wh40k_runtime_logo_paths_are_canonical_gui_files()
    test_wh40k_positive_optical_offset_keeps_logo_contained()
    test_eva_gui_logo_bounds_are_contained_without_clipping()
    test_bundled_onefile_gui_logo_hashes_match_source_gui_hashes()
    test_no_png_gui_logo_assets_exist()
    print("test_gui_logo_source_v71337 PASS")
