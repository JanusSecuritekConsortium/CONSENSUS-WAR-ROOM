from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.manual_visual_review import VALID_REVIEW_STATUSES, record_visual_review


def main() -> int:
    parser = argparse.ArgumentParser(description="Record manual visual review status for a CONSENSUS GUI theme.")
    parser.add_argument("--theme", required=True, help="Theme key or alias.")
    parser.add_argument("--status", required=True, choices=VALID_REVIEW_STATUSES, help="Manual review status.")
    parser.add_argument("--notes", default="", help="Reviewer notes.")
    parser.add_argument("--screenshot-path", default=None, help="Optional screenshot path to record.")
    parser.add_argument("--registry", type=Path, default=None, help="Optional registry JSON path.")
    args = parser.parse_args()

    registry = record_visual_review(
        args.theme,
        args.status,
        notes=args.notes,
        screenshot_path=args.screenshot_path,
        path=args.registry,
    )
    print(json.dumps(registry, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
