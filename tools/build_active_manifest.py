from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from core.active_compile import ACTIVE_COMPILE_TARGETS, EXCLUDED_PARTS


REPORTS_DIR = ROOT / "reports"
ACTIVE_METADATA_FILES = (
    "CHANGELOG.md",
    "README.md",
    "READMEe.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "CONSENSUS_ARCHITECTURE.md",
    "MSTY_STUDIO_INTEGRATION.md",
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


def build_active_manifest(root: Path = ROOT) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(iter_active_manifest_files(root), key=lambda item: item.relative_to(root).as_posix()):
        stat = path.stat()
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
                "size": stat.st_size,
                "modified_timestamp": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "modified_time_ns": stat.st_mtime_ns,
            }
        )
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
