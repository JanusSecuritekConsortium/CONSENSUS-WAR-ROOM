from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.proposals.templates import get_template, list_templates, validate_template_values


def test_templates_include_canonical_ids() -> None:
    ids = {template["id"] for template in list_templates()}
    assert {
        "geopolitical_analysis",
        "market_finance_analysis",
        "technical_decision",
        "operational_risk",
        "general_tribunal_query",
    }.issubset(ids)


def test_missing_required_fields_report_clear_errors() -> None:
    errors = validate_template_values("technical_decision", {"decision": "Ship now"})
    assert "Missing required field: options" in errors
    assert "Missing required field: constraints" in errors


def test_get_template_returns_copy() -> None:
    template = get_template("general_tribunal_query")
    template["title"] = "mutated"
    assert get_template("general_tribunal_query")["title"] == "General Tribunal Query"


if __name__ == "__main__":
    test_templates_include_canonical_ids()
    test_missing_required_fields_report_clear_errors()
    test_get_template_returns_copy()
    print("test_proposal_templates PASS")
