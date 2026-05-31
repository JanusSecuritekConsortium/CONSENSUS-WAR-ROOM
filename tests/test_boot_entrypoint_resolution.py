from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.boot import main as boot_main, run_self_test


def test_executable_launcher_resolves_canonical_boot_entrypoint() -> None:
    import consensus_launcher

    assert consensus_launcher.main is boot_main


def test_build_wrapper_targets_consensus_executable() -> None:
    script = (ROOT / "build_exe.py").read_text(encoding="utf-8")
    batch = (ROOT / "build_exe.bat").read_text(encoding="utf-8")
    assert 'ROOT / "dist" / "CONSENSUS.exe"' in script
    assert "build_exe.py" in batch


def test_real_gui_target_exposes_optional_readiness_marker() -> None:
    source = (ROOT / "ui" / "flet_app.py").read_text(encoding="utf-8")
    assert 'os.getenv("CONSENSUS_GUI_READY_MARKER")' in source
    assert 'write_text("ready", encoding="utf-8")' in source


def test_self_test_validates_packaged_voice_assets_and_simulations() -> None:
    assert run_self_test() == 0


if __name__ == "__main__":
    test_executable_launcher_resolves_canonical_boot_entrypoint()
    test_build_wrapper_targets_consensus_executable()
    test_real_gui_target_exposes_optional_readiness_marker()
    test_self_test_validates_packaged_voice_assets_and_simulations()
    print("test_boot_entrypoint_resolution PASS")
