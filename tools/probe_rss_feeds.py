from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.data_sources.source_config import load_data_source_config
from integrations.rss.probe import probe_feed


def build_probe_report(*, include_disabled: bool = False, include_entries: bool = False) -> dict[str, Any]:
    feeds = load_data_source_config().get("sources", {}).get("rss", {}).get("feeds", [])
    results = []
    for configured in feeds:
        feed = dict(configured)
        if include_disabled:
            feed["enabled"] = True
            feed["quarantined"] = False
        result = probe_feed(feed).to_dict()
        result["entry_count"] = len(result["entries"])
        if not include_entries:
            result.pop("entries", None)
        result["name"] = feed.get("name")
        result["tier"] = feed.get("tier")
        result["taxonomy_tags"] = feed.get("taxonomy_tags", [])
        results.append(result)
    failures = [result for result in results if result["status"] not in {"READY", "DISABLED"}]
    return {
        "status": "READY" if not failures else "DEGRADED",
        "source_count": len(results),
        "failure_count": len(failures),
        "sources": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe configured Bellator RSS/Atom endpoints.")
    parser.add_argument("--include-disabled", action="store_true", help="Probe disabled and quarantined endpoints for operator review.")
    parser.add_argument("--include-entries", action="store_true", help="Include parsed article entries in JSON output.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()
    report = build_probe_report(include_disabled=args.include_disabled, include_entries=args.include_entries)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        for source in report["sources"]:
            print(f"{source['source_id']}: {source['status']} HTTP={source['http_status']} URL={source['final_url']}")
        print(f"RSS PROBE {report['status']}: {report['source_count']} sources, {report['failure_count']} failures")
    return 0 if report["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
