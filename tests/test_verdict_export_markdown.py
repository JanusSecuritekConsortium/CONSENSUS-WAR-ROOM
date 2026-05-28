from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.export.verdict import export_latest_verdict


def test_verdict_export_markdown_contains_verdict_summary() -> None:
    trace = {
        "proposal_id": "prop_test_md",
        "taxonomy": "TECHNICAL_DECISION",
        "votes": {"ARBITER": {"vote": "NO_CONSENSUS"}},
        "confidence": 0.4,
        "final_verdict": "NO_CONSENSUS",
        "terminal_branch": "threshold",
        "review_triggers": ["low_confidence"],
    }
    with tempfile.TemporaryDirectory() as tmp:
        result = export_latest_verdict(trace, output_dir=Path(tmp))
        markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
        assert "# Latest Verdict: prop_test_md" in markdown
        assert "NO_CONSENSUS" in markdown
        assert "TECHNICAL_DECISION" in markdown


if __name__ == "__main__":
    test_verdict_export_markdown_contains_verdict_summary()
    print("test_verdict_export_markdown PASS")
