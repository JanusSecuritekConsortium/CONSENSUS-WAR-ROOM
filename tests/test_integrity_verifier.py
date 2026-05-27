from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_active_manifest import write_active_manifest
from tools.verify_active_manifest import verify_active_manifest


def test_integrity_verifier_reports_clean_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "core").mkdir()
        (root / "core" / "x.py").write_text("x = 1\n", encoding="utf-8")
        manifest = root / "reports" / "active_manifest_TEST.json"
        write_active_manifest(manifest, root)

        result = verify_active_manifest(manifest, root)

    assert result["status"] == "CLEAN"
    assert result["added"] == []
    assert result["removed"] == []
    assert result["modified"] == []


def test_integrity_verifier_reports_added_removed_modified() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "core").mkdir()
        (root / "core" / "x.py").write_text("x = 1\n", encoding="utf-8")
        (root / "core" / "remove_me.py").write_text("y = 1\n", encoding="utf-8")
        manifest = root / "reports" / "active_manifest_TEST.json"
        write_active_manifest(manifest, root)

        (root / "core" / "x.py").write_text("x = 2\n", encoding="utf-8")
        (root / "core" / "remove_me.py").unlink()
        (root / "core" / "added.py").write_text("z = 3\n", encoding="utf-8")
        result = verify_active_manifest(manifest, root)

    assert result["status"] == "DRIFT"
    assert result["added"] == ["core/added.py"]
    assert result["removed"] == ["core/remove_me.py"]
    assert result["modified"] == ["core/x.py"]


def test_integrity_verifier_unknown_without_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = verify_active_manifest(Path(tmp) / "missing.json", Path(tmp))

    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "active_manifest_missing"


if __name__ == "__main__":
    test_integrity_verifier_reports_clean_manifest()
    test_integrity_verifier_reports_added_removed_modified()
    test_integrity_verifier_unknown_without_manifest()
    print("test_integrity_verifier PASS")
