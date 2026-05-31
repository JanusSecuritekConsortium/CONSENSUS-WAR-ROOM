from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_pyinstaller_spec_bundles_runtime_assets_and_metadata() -> None:
    spec = (ROOT / "CONSENSUS.spec").read_text(encoding="utf-8")
    version_info = (ROOT / "packaging" / "windows_version_info.txt").read_text(encoding="utf-8")

    assert 'name="CONSENSUS"' in spec
    assert '"static"' in spec
    assert '"genesis_config.json"' in spec
    assert '"voice_config.json"' in spec
    assert '"consensus_icon.ico"' in spec
    assert '"windows_version_info.txt"' in spec
    assert '"CONSENSUS SYSTEM"' in version_info
    assert '"Janus Securitek Consortium"' in version_info
    assert '"Multi-Agent Tribunal Decision System"' in version_info
    assert '"7.12.1"' in version_info


if __name__ == "__main__":
    test_pyinstaller_spec_bundles_runtime_assets_and_metadata()
    print("test_pyinstaller_spec_exists PASS")
