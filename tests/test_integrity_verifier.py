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


def test_quick_check_reuses_fingerprints_and_still_sees_changes(monkeypatch) -> None:
    import os

    from tools import build_active_manifest as builder

    monkeypatch.setattr(builder, "_hash_cache", {})
    read: list[str] = []
    real_sha256 = builder._sha256
    monkeypatch.setattr(builder, "_sha256", lambda path: read.append(path.name) or real_sha256(path))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "core").mkdir()
        target = root / "core" / "x.py"
        other = root / "core" / "y.py"
        target.write_text("x = 1\n", encoding="utf-8")
        other.write_text("y = 1\n", encoding="utf-8")
        manifest = root / "reports" / "active_manifest_TEST.json"
        write_active_manifest(manifest, root)

        read.clear()
        first = verify_active_manifest(manifest, root, quick=True)
        assert first["status"] == "CLEAN" and first["check"] == "quick"
        assert sorted(read) == ["x.py", "y.py"]

        read.clear()
        assert verify_active_manifest(manifest, root, quick=True)["status"] == "CLEAN"
        assert read == []  # nothing changed, so nothing is read again

        target.write_text("x = 2\n", encoding="utf-8")
        stat = target.stat()
        os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
        changed = verify_active_manifest(manifest, root, quick=True)
        assert changed["status"] == "DRIFT" and changed["modified"] == ["core/x.py"]
        assert read == ["x.py"]  # only the changed file is read

        read.clear()
        full = verify_active_manifest(manifest, root)
        assert full["check"] == "full" and full["modified"] == ["core/x.py"]
        assert sorted(read) == ["x.py", "y.py"]  # the full check always reads everything


def test_quick_check_keeps_only_the_real_tree_on_disk(monkeypatch, tmp_path: Path) -> None:
    from tools import build_active_manifest as builder

    cache_file = tmp_path / "cache" / "integrity_hash_cache.json"
    monkeypatch.setattr(builder, "HASH_CACHE_PATH", cache_file)
    monkeypatch.setattr(builder, "_hash_cache", None)
    root = tmp_path / "tree"
    (root / "core").mkdir(parents=True)
    (root / "core" / "x.py").write_text("x = 1\n", encoding="utf-8")

    builder.build_active_manifest(root, reuse_hashes=True)
    assert not cache_file.exists()  # some other folder: remembered for this run only

    monkeypatch.setattr(builder, "ROOT", root)
    builder.build_active_manifest(root, reuse_hashes=True)
    assert cache_file.exists()

    # A fresh start loads the stored fingerprints and reads no file.
    monkeypatch.setattr(builder, "_hash_cache", None)
    real_sha256 = builder._sha256
    read: list[str] = []
    monkeypatch.setattr(builder, "_sha256", lambda path: read.append(path.name) or real_sha256(path))
    assert builder.build_active_manifest(root, reuse_hashes=True)["file_count"] == 1
    assert read == []

    # A damaged cache file is ignored and rebuilt, not fatal.
    cache_file.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(builder, "_hash_cache", None)
    assert builder.build_active_manifest(root, reuse_hashes=True)["file_count"] == 1
    assert read == ["x.py"]


if __name__ == "__main__":
    test_integrity_verifier_reports_clean_manifest()
    test_integrity_verifier_reports_added_removed_modified()
    test_integrity_verifier_unknown_without_manifest()
    print("test_integrity_verifier PASS")
