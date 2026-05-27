from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.manual_visual_review import default_manual_visual_review_registry, record_visual_review, write_manual_visual_review_registry


def test_record_visual_review_preserves_existing_entries(tmp_path: Path) -> None:
    target = tmp_path / "manual_visual_review.json"
    registry = default_manual_visual_review_registry()
    registry["themes"][0]["reviewer_notes"] = "keep me"
    write_manual_visual_review_registry(registry, target)

    updated = record_visual_review("helldivers", "NEEDS_FIX", "logo too tall", path=target)
    by_theme = {entry["theme"]: entry for entry in updated["themes"]}

    assert by_theme["helldivers"]["status"] == "NEEDS_FIX"
    assert by_theme["helldivers"]["reviewer_notes"] == "logo too tall"
    assert by_theme[registry["themes"][0]["theme"]]["reviewer_notes"] == "keep me"


def test_record_visual_review_cli_updates_registry(tmp_path: Path) -> None:
    target = tmp_path / "manual_visual_review.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "record_visual_review.py"),
            "--theme",
            "helldivers",
            "--status",
            "NEEDS_FIX",
            "--notes",
            "logo too tall",
            "--registry",
            str(target),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    data = json.loads(target.read_text(encoding="utf-8"))
    by_theme = {entry["theme"]: entry for entry in data["themes"]}

    assert completed.returncode == 0
    assert by_theme["helldivers"]["status"] == "NEEDS_FIX"
    assert by_theme["helldivers"]["reviewer_notes"] == "logo too tall"


if __name__ == "__main__":
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        test_record_visual_review_preserves_existing_entries(Path(tmp))
    with TemporaryDirectory() as tmp:
        test_record_visual_review_cli_updates_registry(Path(tmp))
    print("test_record_visual_review PASS")
