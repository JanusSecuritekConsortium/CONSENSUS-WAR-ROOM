from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.assets.app_icon import APP_ICON_ICO, APP_ICON_PNG, APP_ICON_PNG_256, validate_app_icon_assets


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_app_icon_is_consensus_named_asset_not_old_default() -> None:
    status = validate_app_icon_assets()

    assert status["not_old_default"] is True
    assert Path(status["configured_icon"]).name == "consensus_icon.ico"
    assert "flet" not in Path(status["configured_icon"]).name.lower()
    assert "arrow" not in Path(status["configured_icon"]).name.lower()


def test_app_icon_assets_are_distinct_real_icon_files() -> None:
    hashes = {_sha256(APP_ICON_ICO), _sha256(APP_ICON_PNG), _sha256(APP_ICON_PNG_256)}

    assert len(hashes) == 3
    assert APP_ICON_ICO.read_bytes().startswith(b"\x00\x00\x01\x00")
    assert APP_ICON_PNG.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert APP_ICON_PNG_256.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    test_app_icon_is_consensus_named_asset_not_old_default()
    test_app_icon_assets_are_distinct_real_icon_files()
    print("test_app_icon_not_old_default PASS")
