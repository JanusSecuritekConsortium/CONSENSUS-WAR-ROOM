from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from tools.build_active_manifest import REPORTS_DIR, build_active_manifest, write_active_manifest


def latest_active_manifest(reports_dir: Path = REPORTS_DIR) -> Path | None:
    current = reports_dir / f"active_manifest_{SYSTEM_VERSION}.json"
    if current.exists():
        return current
    manifests = [path for path in reports_dir.glob("active_manifest_*.json") if path.is_file()]
    if not manifests:
        return None
    return max(manifests, key=lambda path: path.stat().st_mtime)


def _file_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    files = manifest.get("files", [])
    if not isinstance(files, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in files:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            result[item["path"]] = item
    return result


def verify_active_manifest(manifest_path: Path | None = None, root: Path = ROOT) -> dict[str, Any]:
    baseline_path = manifest_path or latest_active_manifest()
    if baseline_path is None or not baseline_path.exists():
        return {
            "version": SYSTEM_VERSION,
            "status": "UNKNOWN",
            "manifest_path": None,
            "reason": "active_manifest_missing",
            "added": [],
            "removed": [],
            "modified": [],
        }
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "version": SYSTEM_VERSION,
            "status": "UNKNOWN",
            "manifest_path": str(baseline_path),
            "reason": f"active_manifest_unreadable:{exc.__class__.__name__}",
            "added": [],
            "removed": [],
            "modified": [],
        }

    current = build_active_manifest(root)
    baseline_files = _file_map(baseline)
    current_files = _file_map(current)
    baseline_paths = set(baseline_files)
    current_paths = set(current_files)
    added = sorted(current_paths - baseline_paths)
    removed = sorted(baseline_paths - current_paths)
    modified = sorted(
        path
        for path in baseline_paths & current_paths
        if baseline_files[path].get("sha256") != current_files[path].get("sha256")
        or baseline_files[path].get("size") != current_files[path].get("size")
    )
    status = "CLEAN" if not added and not removed and not modified else "DRIFT"
    return {
        "version": SYSTEM_VERSION,
        "status": status,
        "manifest_path": str(baseline_path),
        "baseline_version": baseline.get("version"),
        "current_file_count": current.get("file_count"),
        "baseline_file_count": baseline.get("file_count"),
        "added": added,
        "removed": removed,
        "modified": modified,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify current active tree against the latest integrity manifest.")
    parser.add_argument("--manifest", type=Path, default=None, help="Manifest path to verify against.")
    parser.add_argument("--approve", action="store_true", help="Approve current active tree by writing a new manifest.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON.")
    args = parser.parse_args()

    if args.approve:
        target = write_active_manifest(args.manifest)
        result = verify_active_manifest(target)
        result["approved_manifest_path"] = str(target)
    else:
        result = verify_active_manifest(args.manifest)
    print(json.dumps(result, indent=None if args.compact else 2, ensure_ascii=True))
    return 0 if result.get("status") == "CLEAN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
