from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from core.decision_trace import read_latest_trace
from core.manual_visual_review import manual_visual_review_path, manual_visual_review_summary
from core.paths import SYSTEM_LOG_PATH, WAR_ROOM_RUNTIME_LOG_PATH
from tools.check_dependencies import build_dependency_report
from tools.provider_status_report import build_provider_status_report
from tools.runtime_snapshot import build_runtime_snapshot
from tools.verify_active_manifest import latest_active_manifest, verify_active_manifest


REPORTS_DIR = ROOT / "reports"


def _safe_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True, default=str) + "\n"


def _latest_existing(paths: Iterable[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def _latest_verification_manifest() -> Path | None:
    current = REPORTS_DIR / f"verification_v{SYSTEM_VERSION}.json"
    if current.exists():
        return current
    return _latest_existing(REPORTS_DIR.glob("verification_v*.json"))


def _latest_manual_visual_review_file() -> Path | None:
    current = manual_visual_review_path()
    if current.exists():
        return current
    return _latest_existing(REPORTS_DIR.glob("manual_visual_review_v*.json"))


def _latest_gui_screenshots() -> list[Path]:
    matches: list[Path] = []
    for pattern in ("gui_snapshot_v*.png", "gui_diagnostics_snapshot_v*.png"):
        latest = _latest_existing(REPORTS_DIR.glob(pattern))
        if latest is not None:
            matches.append(latest)
    return matches


def _tail_text(path: Path, line_count: int) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-line_count:]) + ("\n" if lines else "")


def _changelog_excerpt(line_count: int = 80) -> str:
    path = ROOT / "CHANGELOG.md"
    if not path.exists():
        return ""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:line_count]) + "\n"


def export_runtime_bundle(output: Path | None = None, log_lines: int = 200) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output or REPORTS_DIR / f"runtime_bundle_{SYSTEM_VERSION}_{timestamp}.zip"

    snapshot = build_runtime_snapshot()
    provider_status = build_provider_status_report()
    latest_trace = read_latest_trace()
    manifest = _latest_verification_manifest()
    visual_review = _latest_manual_visual_review_file()
    visual_review_summary = manual_visual_review_summary(visual_review) if visual_review is not None else manual_visual_review_summary()
    active_manifest = latest_active_manifest()
    integrity_result = verify_active_manifest(active_manifest)
    dependency_report = build_dependency_report()

    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("runtime_snapshot.json", _safe_json(snapshot))
        bundle.writestr("provider_status.json", _safe_json(provider_status))
        bundle.writestr("latest_decision_trace.json", _safe_json(latest_trace or {}))
        bundle.writestr("integrity_verification.json", _safe_json(integrity_result))
        bundle.writestr("manual_visual_review_summary.json", _safe_json(visual_review_summary))
        bundle.writestr("telemetry_summary.json", _safe_json(snapshot.get("telemetry", {})))
        bundle.writestr("dependency_status.json", _safe_json(dependency_report))
        if manifest is not None:
            bundle.write(manifest, f"reports/{manifest.name}")
            try:
                verification = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                verification = {}
            bundle.writestr("test_duration_report.json", _safe_json(verification.get("duration_report", {})))
        if visual_review is not None and visual_review.exists():
            bundle.write(visual_review, f"reports/{visual_review.name}")
        if active_manifest is not None and active_manifest.exists():
            bundle.write(active_manifest, f"reports/{active_manifest.name}")
        for screenshot in _latest_gui_screenshots():
            bundle.write(screenshot, f"reports/{screenshot.name}")
        bundle.writestr("logs/system_tail.jsonl", _tail_text(SYSTEM_LOG_PATH, log_lines))
        bundle.writestr("logs/war_room_runtime_tail.jsonl", _tail_text(WAR_ROOM_RUNTIME_LOG_PATH, log_lines))
        bundle.writestr("CHANGELOG_excerpt.md", _changelog_excerpt())
        bundle.writestr(
            "manifest.json",
            _safe_json(
                {
                    "version": SYSTEM_VERSION,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "runtime_snapshot": "runtime_snapshot.json",
                    "provider_status": "provider_status.json",
                    "latest_decision_trace": "latest_decision_trace.json",
                    "integrity_verification": "integrity_verification.json",
                    "manual_visual_review_summary": "manual_visual_review_summary.json",
                    "telemetry_summary": "telemetry_summary.json",
                    "dependency_status": "dependency_status.json",
                    "test_duration_report": "test_duration_report.json",
                    "screenshot_status": snapshot.get("screenshot_status")
                    or snapshot.get("visual_review", {}).get("screenshot_status")
                    or visual_review_summary.get("screenshot_status"),
                    "verification_manifest": f"reports/{manifest.name}" if manifest is not None else None,
                    "manual_visual_review_file": f"reports/{visual_review.name}" if visual_review is not None else None,
                    "active_manifest": f"reports/{active_manifest.name}" if active_manifest is not None else None,
                    "gui_screenshots": [f"reports/{path.name}" for path in _latest_gui_screenshots()],
                    "runtime_logs": ["logs/system_tail.jsonl", "logs/war_room_runtime_tail.jsonl"],
                    "changelog_excerpt": "CHANGELOG_excerpt.md",
                }
            ),
        )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a CONSENSUS runtime observability bundle.")
    parser.add_argument("--output", type=Path, default=None, help="Bundle ZIP path.")
    parser.add_argument("--log-lines", type=int, default=200, help="Runtime log lines to include.")
    args = parser.parse_args()
    target = export_runtime_bundle(args.output, args.log_lines)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
