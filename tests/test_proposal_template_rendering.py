from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.proposals.templates import get_template, render_template, render_template_draft


def test_render_template_requires_fields() -> None:
    try:
        render_template("general_tribunal_query", {})
    except ValueError as exc:
        assert "Missing required field: query" in str(exc)
    else:
        raise AssertionError("render_template accepted missing required fields")


def test_render_template_outputs_structured_text() -> None:
    rendered = render_template(
        "operational_risk",
        {"operation": "Data center move", "threats": "Outage", "impact": "High"},
    )
    assert "Title: Operational Risk" in rendered
    assert "Taxonomy hint: OPERATIONAL_RISK" in rendered
    assert "Data center move" in rendered


def test_draft_render_does_not_mutate_template() -> None:
    before = get_template("market_finance_analysis")
    draft = render_template_draft("market_finance_analysis")
    after = get_template("market_finance_analysis")
    assert "[ASSET_OR_MARKET]" in draft
    assert before == after


if __name__ == "__main__":
    test_render_template_requires_fields()
    test_render_template_outputs_structured_text()
    test_draft_render_does_not_mutate_template()
    print("test_proposal_template_rendering PASS")
