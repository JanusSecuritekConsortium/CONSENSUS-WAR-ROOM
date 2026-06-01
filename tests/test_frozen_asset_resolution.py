from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.paths import resolve_resource_root, resolve_system_root


def test_frozen_resource_root_uses_meipass_and_state_root_uses_executable_dir() -> None:
    original_frozen = getattr(sys, "frozen", None)
    original_meipass = getattr(sys, "_MEIPASS", None)
    original_executable = sys.executable
    try:
        with tempfile.TemporaryDirectory() as tmp:
            extraction = Path(tmp) / "onefile_resources"
            executable = Path(tmp) / "dist" / "CONSENSUS.exe"
            extraction.mkdir()
            executable.parent.mkdir()
            sys.frozen = True  # type: ignore[attr-defined]
            sys._MEIPASS = str(extraction)  # type: ignore[attr-defined]
            sys.executable = str(executable)
            assert resolve_resource_root() == extraction.resolve()
            assert resolve_system_root() == executable.parent.resolve()
    finally:
        sys.executable = original_executable
        if original_frozen is None:
            delattr(sys, "frozen")
        else:
            sys.frozen = original_frozen  # type: ignore[attr-defined]
        if original_meipass is None:
            delattr(sys, "_MEIPASS")
        else:
            sys._MEIPASS = original_meipass  # type: ignore[attr-defined]


def test_spec_bundles_static_assets_for_frozen_resolution() -> None:
    spec = (ROOT / "CONSENSUS.spec").read_text(encoding="utf-8")
    assert '(str(ROOT / "static"), "static")' in spec


if __name__ == "__main__":
    test_frozen_resource_root_uses_meipass_and_state_root_uses_executable_dir()
    test_spec_bundles_static_assets_for_frozen_resolution()
    print("test_frozen_asset_resolution PASS")
