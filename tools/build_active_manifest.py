from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from core.active_compile import ACTIVE_COMPILE_TARGETS, EXCLUDED_PARTS


REPORTS_DIR = ROOT / "reports"
# Fingerprints already worked out, so the routine status check does not re-read
# every file. A file counts as unchanged while its size and modified time match.
HASH_CACHE_PATH = ROOT / ".local" / "integrity_hash_cache.json"
_hash_cache: dict[str, list[Any]] | None = None
_hash_cache_on_disk: dict[str, list[Any]] = {}
_hash_cache_lock = threading.Lock()
ACTIVE_METADATA_FILES = (
    "CHANGELOG.md",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "docs/ARCHITECTURE.md",
    "docs/MSTY_STUDIO_INTEGRATION.md",
)
MANIFEST_EXCLUDED_PARTS = {
    *EXCLUDED_PARTS,
    "archive",
    "legacy",
    "runtime",
    "generated",
    "cache",
    "logs",
    "reports",
}


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return bool(set(parts) & MANIFEST_EXCLUDED_PARTS)


def iter_active_manifest_files(root: Path = ROOT) -> Iterable[Path]:
    targets = [*ACTIVE_COMPILE_TARGETS, *ACTIVE_METADATA_FILES]
    seen: set[Path] = set()
    for target_name in targets:
        target = root / target_name
        if not target.exists() or _is_excluded(target, root):
            continue
        if target.is_file():
            if target not in seen:
                seen.add(target)
                yield target
            continue
        for path in target.rglob("*"):
            if path.is_dir() or _is_excluded(path, root):
                continue
            if path not in seen:
                seen.add(path)
                yield path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_hash_cache() -> dict[str, list[Any]]:
    global _hash_cache, _hash_cache_on_disk
    if _hash_cache is None:
        try:
            loaded = json.loads(HASH_CACHE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            loaded = {}
        _hash_cache = {
            key: value for key, value in loaded.items()
            if isinstance(value, list) and len(value) == 3 and isinstance(value[2], str)
        } if isinstance(loaded, dict) else {}
        _hash_cache_on_disk = dict(_hash_cache)
    return _hash_cache


def _save_hash_cache(entries: dict[str, list[Any]]) -> None:
    """Best effort: a cache that cannot be written only costs time on the next start."""
    global _hash_cache_on_disk
    _hash_cache_on_disk = dict(entries)
    temporary = HASH_CACHE_PATH.with_name(f"{HASH_CACHE_PATH.name}.{os.getpid()}.tmp")
    try:
        HASH_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(entries, ensure_ascii=True), encoding="utf-8")
        os.replace(temporary, HASH_CACHE_PATH)
    except OSError:
        try:
            temporary.unlink()
        except OSError:
            pass


def build_active_manifest(root: Path = ROOT, reuse_hashes: bool = False) -> dict[str, Any]:
    """Fingerprint every active file. With reuse_hashes, a file whose size and
    modified time are unchanged keeps the fingerprint worked out earlier instead
    of being read again; the default reads every file in full."""
    files: list[dict[str, Any]] = []
    seen: dict[str, list[Any]] = {}
    with _hash_cache_lock:
        cache = _load_hash_cache() if reuse_hashes else {}
        for path in sorted(iter_active_manifest_files(root), key=lambda item: item.relative_to(root).as_posix()):
            stat = path.stat()
            key = str(path)
            known = cache.get(key)
            if known is not None and known[0] == stat.st_size and known[1] == stat.st_mtime_ns:
                digest = known[2]
            else:
                digest = _sha256(path)
            seen[key] = [stat.st_size, stat.st_mtime_ns, digest]
            files.append(_manifest_entry(path, root, stat, digest))
        if reuse_hashes:
            cache.update(seen)
            # Only the real tree is kept on disk, and only files that still exist.
            if root == ROOT and seen != _hash_cache_on_disk:
                _save_hash_cache(seen)
    return _manifest(root, files)


def _manifest_entry(path: Path, root: Path, stat: os.stat_result, digest: str) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": digest,
        "size": stat.st_size,
        "modified_timestamp": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "modified_time_ns": stat.st_mtime_ns,
    }


def _manifest(root: Path, files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": SYSTEM_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "excluded_parts": sorted(MANIFEST_EXCLUDED_PARTS),
        "file_count": len(files),
        "files": files,
    }


def write_active_manifest(output: Path | None = None, root: Path = ROOT) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    target = output or REPORTS_DIR / f"active_manifest_{SYSTEM_VERSION}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_active_manifest(root)
    target.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the CONSENSUS active tree integrity manifest.")
    parser.add_argument("--output", type=Path, default=None, help="Manifest output path.")
    args = parser.parse_args()
    target = write_active_manifest(args.output)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
