from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from core.manual_visual_review import (
    default_manual_visual_review_registry,
    load_manual_visual_review_registry,
    manual_visual_review_summary,
    write_manual_visual_review_registry,
)
from ui.themes.catalog import get_gui_theme_options


def test_default_manual_visual_review_registry_covers_gui_themes() -> None:
    registry = default_manual_visual_review_registry()
    themes = {entry["theme"] for entry in registry["themes"]}

    assert registry["version"] == SYSTEM_VERSION
    assert registry["screenshot_status"] == "MANUAL_REVIEW_REQUIRED"
    assert themes == {theme.key for theme in get_gui_theme_options()}
    assert {entry["status"] for entry in registry["themes"]} == {"PENDING"}


def test_manual_visual_review_summary_counts_statuses(tmp_path: Path) -> None:
    target = tmp_path / "manual_visual_review.json"
    registry = default_manual_visual_review_registry()
    registry["themes"][0]["status"] = "APPROVED"
    registry["themes"][1]["status"] = "NEEDS_FIX"
    write_manual_visual_review_registry(registry, target)

    loaded = load_manual_visual_review_registry(target)
    summary = manual_visual_review_summary(target)

    assert loaded["themes"][0]["status"] == "APPROVED"
    assert summary["approved_count"] == 1
    assert summary["needs_fix_count"] == 1
    assert summary["action_required_count"] == 1


if __name__ == "__main__":
    from tempfile import TemporaryDirectory

    test_default_manual_visual_review_registry_covers_gui_themes()
    with TemporaryDirectory() as tmp:
        test_manual_visual_review_summary_counts_statuses(Path(tmp))
    print("test_manual_visual_review_registry PASS")
