from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export.simulation import export_simulation_dossier


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a deterministic CONSENSUS simulation dossier.")
    parser.add_argument("scenario_id", help="Stored simulation scenario id.")
    args = parser.parse_args()
    exported = export_simulation_dossier(args.scenario_id)
    print(exported["json_path"])
    print(exported["markdown_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
