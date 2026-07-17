from __future__ import annotations

import sys
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_pyinstaller_spec_bundles_runtime_assets_and_metadata() -> None:
    spec = (ROOT / "CONSENSUS.spec").read_text(encoding="utf-8")
    version_info = (ROOT / "packaging" / "windows_version_info.txt").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    from config.version import SYSTEM_VERSION

    package_version_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert package_version_match is not None
    package_version = package_version_match.group(1)
    version_tuple = ", ".join([*package_version.split("."), "0"])

    assert 'name="CONSENSUS"' in spec
    assert '"static"' in spec
    assert '"genesis_config.json"' in spec
    assert '"voice_config.json"' in spec
    assert '"consensus_icon.ico"' in spec
    assert '"windows_version_info.txt"' in spec
    assert '"CONSENSUS SYSTEM"' in version_info
    assert '"Janus Securitek Consortium"' in version_info
    assert '"Multi-Agent Tribunal Decision System"' in version_info
    assert package_version == SYSTEM_VERSION
    assert f"filevers=({version_tuple})" in version_info
    assert f"prodvers=({version_tuple})" in version_info
    assert f'"FileVersion", "{SYSTEM_VERSION}"' in version_info
    assert f'"ProductVersion", "{SYSTEM_VERSION}"' in version_info


if __name__ == "__main__":
    test_pyinstaller_spec_bundles_runtime_assets_and_metadata()
    print("test_pyinstaller_spec_exists PASS")
