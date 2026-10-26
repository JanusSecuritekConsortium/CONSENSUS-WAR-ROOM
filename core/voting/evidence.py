"""Host passage checks. Quote anchoring is not semantic or factual verification."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any


def _text(value: str) -> str:
    return " ".join(value.split())


def supplied_passages(query: str, context: dict) -> list[dict]:
    records = [{"source": "proposal", "text": query, "kind": "assertion"}]

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            source = value.get("source_url") or value.get("url") or value.get("source_id") or value.get("source")
            text = value.get("excerpt") or value.get("text") or value.get("body")
            if isinstance(source, str) and isinstance(text, str) and text.strip():
                record = {"source": source, "text": text, "kind": "reference"}
                for key in ("published_at", "page", "max_age_days"):
                    if key in value:
                        record[key] = value[key]
                if record not in records:
                    records.append(record)
            for key, item in value.items():
                if key not in {"deliberation", "system_prompt", "evidence_passages", "claim_reviews"}:
                    collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(context)
    return records


def audit_evidence(argument: dict, context: dict, now: datetime | None = None) -> list[dict]:
    """Semantic reviews must be host supplied and match the exact claim and quote."""
    now = now or datetime.now(timezone.utc)
    records = context.get("evidence_passages", []) or []
    audits = []
    evidence = argument.get("evidence", [])
    if not isinstance(evidence, list):
        return audits
    for item in evidence:
        if not isinstance(item, dict):
            continue
        source, quote = item.get("source"), item.get("quote")
        candidates = [r for r in records if isinstance(r, dict) and r.get("source") == source]
        anchored = [r for r in candidates if isinstance(quote, str) and _text(quote) and _text(quote) in _text(r.get("text", ""))]
        audit = {"source": source, "anchor": "matched" if anchored else ("mismatch" if quote else "not_quoted"),
                 "support": "unreviewed", "freshness": "not_required"}
        if quote and not candidates:
            audit["anchor"] = "passage_unavailable"
        matches = anchored or candidates
        freshness = []
        for record in matches:
            if "max_age_days" not in record:
                continue
            try:
                days = float(record["max_age_days"])
                published = datetime.fromisoformat(str(record.get("published_at", "")).replace("Z", "+00:00"))
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                age = (now - published).total_seconds() / 86400
                freshness.append("unknown" if not math.isfinite(days) or days < 0 or age < 0 else ("stale" if age > days else "current"))
            except (ValueError, TypeError, OverflowError):
                freshness.append("unknown")
        if freshness:
            audit["freshness"] = "current" if "current" in freshness else ("unknown" if "unknown" in freshness else "stale")
        reviews = [review for review in context.get("host_claim_reviews", [])
                   if anchored and isinstance(review, dict) and review.get("source") == source
                   and review.get("claim") == argument.get("claim")
                   and _text(str(review.get("quote", ""))) == _text(quote)
                   and review.get("reviewer") and review.get("verdict") in {"supports", "contradicts"}]
        if reviews:
            audit["support"] = "contradicts" if any(r["verdict"] == "contradicts" for r in reviews) else "supports"
        audits.append(audit)
    return audits
