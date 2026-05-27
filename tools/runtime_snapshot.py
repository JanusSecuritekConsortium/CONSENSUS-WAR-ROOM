from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import load_runtime_config
from config.version import SYSTEM_VERSION
from core.decision_trace import read_latest_trace
from core.manual_visual_review import manual_visual_review_summary
from core.paths import CONFIG_PATH, WAR_ROOM_RUNTIME_LOG_PATH
from core.telemetry import TELEMETRY_HISTORY, sample_telemetry
from integrations.msty.api import health_check
from tools.check_dependencies import build_dependency_report
from tools.verify_active_manifest import verify_active_manifest


def health_badge_from_snapshot(snapshot: Dict[str, Any] | None) -> Dict[str, str]:
    if not isinstance(snapshot, dict):
        return {"label": "ERROR", "color_role": "error", "reason": "snapshot_unavailable"}

    status = str(snapshot.get("provider_status") or "").lower()
    missing_models = snapshot.get("missing_models") or {}
    degraded_reason = snapshot.get("degraded_reason")
    if snapshot.get("error"):
        return {"label": "ERROR", "color_role": "error", "reason": str(snapshot.get("error"))}
    if status == "ready" and not missing_models and not degraded_reason:
        return {"label": "READY", "color_role": "primary", "reason": "provider_ready"}
    if status in {"", "unknown", "error"}:
        return {"label": "ERROR", "color_role": "error", "reason": degraded_reason or "provider_status_unknown"}
    return {"label": "DEGRADED", "color_role": "warning", "reason": degraded_reason or "provider_degraded"}


def _latest_jsonl_record(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            return record
    return None


def _test_manifest_path() -> str:
    return str(ROOT / "reports" / f"verification_v{SYSTEM_VERSION}.json")


def build_runtime_snapshot(config_path: Path | None = None) -> Dict[str, Any]:
    config = load_runtime_config(config_path or CONFIG_PATH)
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    provider = health_check(config, nodes)
    visual_review = manual_visual_review_summary()
    dependency_status = build_dependency_report()
    telemetry = sample_telemetry(TELEMETRY_HISTORY)
    snapshot = {
        "version": SYSTEM_VERSION,
        "backend": config.backend,
        "provider_status": provider.get("status"),
        "active_models": provider.get("models", []),
        "missing_models": provider.get("missing_required_models", {}),
        "degraded_reason": provider.get("degraded_reason"),
        "war_room_layout_guard": {
            "main_column_expand": [2, 6, 2],
            "footer_fixed": True,
            "diagnostics_overlay": True,
        },
        "render_guard_status": {
            "enabled": True,
            "state_field": "render_in_progress",
            "reentrant_event": "ui_render_skipped_reentrant",
        },
        "latest_decision_trace": read_latest_trace(),
        "latest_runtime_log": _latest_jsonl_record(WAR_ROOM_RUNTIME_LOG_PATH),
        "test_manifest_path": _test_manifest_path(),
        "integrity_status": verify_active_manifest(),
        "screenshot_status": visual_review.get("screenshot_status", "MANUAL_REVIEW_REQUIRED"),
        "visual_review": visual_review,
        "dependency_status": dependency_status,
        "telemetry": telemetry,
    }
    snapshot["health_badge"] = health_badge_from_snapshot(snapshot)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a CONSENSUS runtime observability snapshot.")
    parser.add_argument("--config", type=Path, default=None, help="Runtime config path.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON.")
    args = parser.parse_args()
    print(json.dumps(build_runtime_snapshot(args.config), indent=None if args.compact else 2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
