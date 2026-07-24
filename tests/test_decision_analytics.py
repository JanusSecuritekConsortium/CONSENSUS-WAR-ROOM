from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path

from core.analytics.decision_metrics import load_decisions, summarize_decisions, summary_to_csv


def _records():
    return [
        {
            "timestamp": "2026-07-23T10:00:00+00:00",
            "verdict": "APPROVED",
            "confidence": 0.8,
            "terminal_branch": "majority",
            "votes": {
                "RATIONALIS": {"vote": "APPROVE", "confidence": 0.9, "response_time": 1.0},
                "AETERNUM": {"vote": "APPROVE", "confidence": 0.8, "response_time": 2.0},
                "BELLATOR": {"vote": "DENY", "confidence": 0.7, "response_time": 3.0},
            },
        },
        {
            "timestamp": "2026-07-24T11:00:00+00:00",
            "verdict": "DENY",
            "confidence": 0.7,
            "terminal_branch": "majority",
            "votes": {
                "RATIONALIS": {"vote": "DENY", "confidence": 0.7, "response_time": 4.0},
                "AETERNUM": {"vote": "DENY", "confidence": 0.6, "response_time": 5.0},
                "BELLATOR": {"vote": "DENY", "confidence": 0.8, "response_time": 6.0},
            },
        },
    ]


def test_summary_reports_bounded_operational_metrics() -> None:
    summary = summarize_decisions(_records())
    assert summary["decision_count"] == 2
    assert summary["verdicts"]["counts"] == {"APPROVE": 1, "DENY": 1}
    assert summary["period"]["calendar_days"] == 2
    assert summary["confidence"]["mean"] == 0.75
    assert summary["response_time_seconds"]["p95"] == 5.75
    assert summary["agreement"]["unanimous_rate"] == 0.5
    assert summary["agreement"]["majority_split_rate"] == 0.5
    assert summary["agreement"]["pairwise"]["AETERNUM|RATIONALIS"]["agreement_rate"] == 1.0
    assert summary["agents"]["BELLATOR"]["vote_distribution"] == {"DENY": 2}


def test_summary_csv_is_flat_and_machine_readable() -> None:
    rows = list(csv.DictReader(StringIO(summary_to_csv(summarize_decisions(_records())))))
    assert rows
    assert set(rows[0]) == {"category", "subject", "metric", "value"}
    assert {
        (row["category"], row["subject"], row["metric"], row["value"])
        for row in rows
    } >= {
        ("system", "all", "decision_count", "2"),
        ("verdicts", "APPROVE", "count", "1"),
        ("agent", "RATIONALIS", "vote_count", "2"),
    }


def test_corrupt_or_non_list_history_degrades_to_empty(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    path.write_text("not-json", encoding="utf-8")
    assert load_decisions(path) == []
    path.write_text(json.dumps({"records": []}), encoding="utf-8")
    assert load_decisions(path) == []
