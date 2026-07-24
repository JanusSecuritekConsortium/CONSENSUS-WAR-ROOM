from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

try:
    from ..core.paths import SYSTEM_ROOT
except ImportError:
    from core.paths import SYSTEM_ROOT


ASSET_MANIFEST_PATH = Path(__file__).with_name("native_glados_assets.json")


def default_native_project_dir() -> Path:
    preferred = SYSTEM_ROOT / "external" / "glados-tts" / "glados-tts-main"
    if preferred.exists():
        return preferred
    return SYSTEM_ROOT / "_ARBITER" / "Bot" / "Voice" / "glados-tts-main"


def inspect_native_glados_assets(project_dir: Path | None = None, *, verify_hashes: bool = False) -> Dict[str, Any]:
    root = project_dir or default_native_project_dir()
    manifest = json.loads(ASSET_MANIFEST_PATH.read_text(encoding="utf-8"))
    files = []
    ready = root.exists()
    for relative, expected in manifest["required"].items():
        path = root / Path(relative)
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        pointer = exists and _is_lfs_pointer(path)
        size_ok = exists and size == int(expected["bytes"])
        hash_value = _sha256(path) if verify_hashes and size_ok else None
        hash_ok = hash_value == expected["sha256"] if hash_value is not None else None
        valid = exists and size_ok and not pointer and hash_ok is not False
        ready = ready and valid
        files.append(
            {
                "relative_path": relative,
                "path": str(path),
                "exists": exists,
                "bytes": size,
                "expected_bytes": int(expected["bytes"]),
                "lfs_pointer": pointer,
                "sha256": hash_value,
                "hash_ok": hash_ok,
                "valid": valid,
            }
        )
    return {
        "ready": ready,
        "project_dir": str(root),
        "source": manifest["source"],
        "license": manifest["license"],
        "files": files,
    }


def native_glados_error(project_dir: Path | None = None, *, verify_hashes: bool = False) -> str:
    status = inspect_native_glados_assets(project_dir, verify_hashes=verify_hashes)
    if status["ready"]:
        return ""
    failures = []
    for item in status["files"]:
        if item["valid"]:
            continue
        if not item["exists"]:
            reason = "missing"
        elif item["lfs_pointer"]:
            reason = "Git LFS pointer only"
        elif item["bytes"] != item["expected_bytes"]:
            reason = f"unexpected size {item['bytes']}"
        elif item["hash_ok"] is False:
            reason = "SHA-256 mismatch"
        else:
            reason = "invalid"
        failures.append(f"{item['relative_path']} ({reason})")
    return "native GLaDOS assets unavailable: " + ", ".join(failures)


def _is_lfs_pointer(path: Path) -> bool:
    if path.stat().st_size > 1024:
        return False
    try:
        return path.read_bytes().startswith(b"version https://git-lfs.github.com/spec/v1")
    except OSError:
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


__all__ = [
    "ASSET_MANIFEST_PATH",
    "default_native_project_dir",
    "inspect_native_glados_assets",
    "native_glados_error",
]
