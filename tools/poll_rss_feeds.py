from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data_sources.rss_backbone import RssIntelligenceBackbone


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll Bellator RSS intelligence feeds into the local SQLite cache.")
    parser.add_argument("--force", action="store_true", help="Poll immediately, ignoring per-source next-poll timestamps.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--watch", action="store_true", help="Continue polling at the configured RSS interval.")
    args = parser.parse_args()
    backbone = RssIntelligenceBackbone()
    while True:
        summary = backbone.poll(force=args.force)
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=True), flush=True)
        else:
            print(
                f"RSS POLL {summary['status']}: attempted={summary['attempted']} skipped={summary['skipped']} "
                f"failed={summary['failed']} stored={summary['stored']} deduplicated={summary['deduplicated']}",
                flush=True,
            )
        if not args.watch:
            return 0 if summary["status"] == "READY" else 1
        time.sleep(backbone.poll_interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
