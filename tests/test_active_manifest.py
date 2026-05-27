from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_active_manifest import build_active_manifest, write_active_manifest


def test_active_manifest_hashes_active_files_and_excludes_generated_roots() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "config").mkdir()
        (root / "config" / "version.py").write_text('SYSTEM_VERSION = "TEST"\n', encoding="utf-8")
        (root / "reports").mkdir()
        (root / "reports" / "generated.json").write_text("{}", encoding="utf-8")
        (root / "archive").mkdir()
        (root / "archive" / "old.py").write_text("x = 1\n", encoding="utf-8")

        manifest = build_active_manifest(root)
        paths = {item["path"] for item in manifest["files"]}

    assert "config/version.py" in paths
    assert "reports/generated.json" not in paths
    assert "archive/old.py" not in paths
    record = next(item for item in manifest["files"] if item["path"] == "config/version.py")
    assert len(record["sha256"]) == 64
    assert record["size"] > 0
    assert record["modified_timestamp"]


def test_write_active_manifest_outputs_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "tools").mkdir()
        (root / "tools" / "x.py").write_text("x = 1\n", encoding="utf-8")
        output = root / "reports" / "active_manifest_TEST.json"

        target = write_active_manifest(output, root)

        assert target == output
        assert output.exists()
        assert "tools/x.py" in output.read_text(encoding="utf-8")


if __name__ == "__main__":
    test_active_manifest_hashes_active_files_and_excludes_generated_roots()
    test_write_active_manifest_outputs_json()
    print("test_active_manifest PASS")
