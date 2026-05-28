from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export.verdict import export_latest_verdict


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the latest decision trace verdict as Markdown and JSON.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    args = parser.parse_args()
    result = export_latest_verdict()
    if args.json:
        print(json.dumps({"json_path": result["json_path"], "markdown_path": result["markdown_path"]}, indent=2))
    else:
        print(f"JSON: {result['json_path']}")
        print(f"Markdown: {result['markdown_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
