from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.app_icon import APP_ICON_ICO, APP_ICON_PNG, APP_ICON_PNG_256, validate_app_icon_assets


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    assert header.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">II", header[16:24])


def test_app_icon_assets_exist_and_are_readable() -> None:
    status = validate_app_icon_assets()

    assert status["status"] == "READY"
    for path in (APP_ICON_ICO, APP_ICON_PNG, APP_ICON_PNG_256):
        record = status["assets"][path.name]
        assert record["exists"] is True
        assert record["extension_ok"] is True
        assert record["non_empty"] is True
        assert record["readable"] is True


def test_app_icon_png_dimensions_are_icon_safe() -> None:
    assert _png_size(APP_ICON_PNG) == (64, 64)
    assert _png_size(APP_ICON_PNG_256) == (256, 256)


if __name__ == "__main__":
    test_app_icon_assets_exist_and_are_readable()
    test_app_icon_png_dimensions_are_icon_safe()
    print("test_app_icon_asset_exists PASS")
