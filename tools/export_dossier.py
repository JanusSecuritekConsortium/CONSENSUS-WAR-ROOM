from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export.dossier import export_dossier


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a combined proposal and verdict dossier.")
    parser.add_argument("proposal_id", help="Proposal history ID to export.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    args = parser.parse_args()
    result = export_dossier(args.proposal_id)
    output = {"json_path": result["json_path"], "markdown_path": result["markdown_path"]}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"JSON: {output['json_path']}")
        print(f"Markdown: {output['markdown_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
