from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from config.version import SYSTEM_VERSION
from core.paths import SYSTEM_ROOT
from ui.themes.catalog import get_gui_theme_options, resolve_theme_key


REPORTS_DIR = SYSTEM_ROOT / "reports"
VALID_REVIEW_STATUSES = ("PENDING", "APPROVED", "REJECTED", "NEEDS_FIX", "NEEDS_REVIEW")


def manual_visual_review_path(version: str = SYSTEM_VERSION) -> Path:
    return REPORTS_DIR / f"manual_visual_review_v{version}.json"


def valid_review_themes() -> tuple[str, ...]:
    return tuple(theme.key for theme in get_gui_theme_options())


def _default_entry(theme: str) -> Dict[str, Any]:
    return {
        "theme": theme,
        "screenshot_path": str(REPORTS_DIR / "theme_gallery" / f"{theme}_v{SYSTEM_VERSION}.png"),
        "status": "PENDING",
        "reviewer_notes": "",
        "reviewed_at": None,
    }


def default_manual_visual_review_registry(version: str = SYSTEM_VERSION) -> Dict[str, Any]:
    return {
        "version": version,
        "screenshot_status": "MANUAL_REVIEW_REQUIRED",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "themes": [_default_entry(theme) for theme in valid_review_themes()],
    }


def _normalize_registry(raw: Dict[str, Any] | None, version: str = SYSTEM_VERSION) -> Dict[str, Any]:
    registry = default_manual_visual_review_registry(version)
    existing_by_theme: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, dict):
        for entry in raw.get("themes", []):
            if isinstance(entry, dict) and isinstance(entry.get("theme"), str):
                key = resolve_theme_key(entry["theme"])
                if key in valid_review_themes():
                    existing_by_theme[key] = entry
    merged = []
    for entry in registry["themes"]:
        theme = entry["theme"]
        preserved = {**entry, **existing_by_theme.get(theme, {})}
        preserved["theme"] = theme
        if preserved.get("status") not in VALID_REVIEW_STATUSES:
            preserved["status"] = "PENDING"
        merged.append(preserved)
    registry["themes"] = merged
    if isinstance(raw, dict):
        registry["screenshot_status"] = raw.get("screenshot_status") or registry["screenshot_status"]
    return registry


def load_manual_visual_review_registry(path: Path | None = None) -> Dict[str, Any]:
    target = path or manual_visual_review_path()
    if not target.exists():
        registry = default_manual_visual_review_registry()
        write_manual_visual_review_registry(registry, target)
        return registry
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = None
    return _normalize_registry(raw)


def write_manual_visual_review_registry(registry: Dict[str, Any], path: Path | None = None) -> Path:
    target = path or manual_visual_review_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    registry = _normalize_registry(registry)
    registry["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(registry, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temp.replace(target)
    return target


def record_visual_review(
    theme: str,
    status: str,
    notes: str = "",
    screenshot_path: str | None = None,
    path: Path | None = None,
) -> Dict[str, Any]:
    normalized_theme = resolve_theme_key(theme)
    if normalized_theme not in valid_review_themes():
        raise ValueError(f"Unknown visual review theme: {theme}")
    normalized_status = status.upper()
    if normalized_status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Invalid visual review status: {status}")

    registry = load_manual_visual_review_registry(path)
    reviewed_at = datetime.now(timezone.utc).isoformat(timespec="seconds") if normalized_status != "PENDING" else None
    for entry in registry["themes"]:
        if entry["theme"] == normalized_theme:
            entry["status"] = normalized_status
            entry["reviewer_notes"] = notes
            entry["reviewed_at"] = reviewed_at
            if screenshot_path is not None:
                entry["screenshot_path"] = screenshot_path
            break
    write_manual_visual_review_registry(registry, path)
    return registry


def manual_visual_review_summary(path: Path | None = None) -> Dict[str, Any]:
    target = path or manual_visual_review_path()
    registry = load_manual_visual_review_registry(target)
    themes = registry.get("themes", [])
    pending = sum(1 for entry in themes if entry.get("status") == "PENDING")
    rejected = sum(1 for entry in themes if entry.get("status") == "REJECTED")
    needs_fix = sum(1 for entry in themes if entry.get("status") == "NEEDS_FIX")
    needs_review = sum(1 for entry in themes if entry.get("status") == "NEEDS_REVIEW")
    approved = sum(1 for entry in themes if entry.get("status") == "APPROVED")
    return {
        "path": str(target),
        "screenshot_status": registry.get("screenshot_status", "MANUAL_REVIEW_REQUIRED"),
        "pending_count": pending,
        "approved_count": approved,
        "rejected_count": rejected,
        "needs_fix_count": needs_fix,
        "needs_review_count": needs_review,
        "action_required_count": rejected + needs_fix + needs_review,
        "themes": themes,
    }


def ensure_manual_visual_review_registry(path: Path | None = None) -> Path:
    target = path or manual_visual_review_path()
    write_manual_visual_review_registry(load_manual_visual_review_registry(target), target)
    return target
