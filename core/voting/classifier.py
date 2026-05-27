from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, Optional

from core.models import Vote


DEFAULT_KEYWORD_MAP: Dict[str, tuple[str, ...]] = {
    "logic": ("logic", "reason", "consisten", "premise", "fallacy", "infer"),
    "governance": ("governance", "policy", "regulat", "compliance", "charter", "mandate"),
    "ethics": ("ethic", "moral", "fairness", "rights", "harm", "consent"),
    "analysis": ("analy", "evaluat", "assess", "breakdown", "diagnos", "review", "validat", "approv", "proposal", "test"),
    "finance": ("financ", "budget", "cost", "revenue", "capital", "invest", "funding"),
    "forecasting": ("forecast", "predict", "projection", "outlook", "trend"),
    "economics": ("econom", "market", "inflation", "supply", "demand", "gdp", "trade"),
    "historical_patterns": ("histor", "precedent", "pattern", "prior", "past", "legacy"),
    "security": ("secur", "vulnerab", "threat", "breach", "attack", "exploit", "intrusion"),
    "geopolitics": ("geopolit", "nation", "sovereign", "treaty", "border", "diplom", "alliance"),
    "risk": ("risk", "downside", "hazard", "exposure", "danger", "liabilit"),
    "operations": ("operation", "logistic", "deploy", "execution", "ops", "rollout", "runtime"),
}

CLOSED_PROPOSAL_TAXONOMY: tuple[str, ...] = tuple(DEFAULT_KEYWORD_MAP)


@dataclass(frozen=True)
class ProposalClassification:
    proposal_classes: tuple[str, ...]
    primary_class: str
    classifier_confidence: float
    classifier_version: str
    classified_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_classes": list(self.proposal_classes),
            "primary_class": self.primary_class,
            "classifier_confidence": self.classifier_confidence,
            "classifier_version": self.classifier_version,
            "classified_at": self.classified_at,
        }


@dataclass(frozen=True)
class ClassificationResult:
    ok: bool
    classification: Optional[ProposalClassification] = None
    failure_reason: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _keyword_hits(text: str, taxonomy: tuple[str, ...], keyword_map: Dict[str, tuple[str, ...]]) -> dict[str, int]:
    lowered = text.lower()
    hits: dict[str, int] = {}
    for proposal_class in taxonomy:
        count = 0
        for stem in keyword_map.get(proposal_class, ()):
            count += len(re.findall(r"(?<![a-z])" + re.escape(stem), lowered))
        if count:
            hits[proposal_class] = count
    return hits


def classify_proposal(
    text: str,
    *,
    taxonomy: Iterable[str],
    confidence_threshold: float,
    keyword_map: Optional[Dict[str, tuple[str, ...]]] = None,
    classifier_version: str = "1.0.0",
    now_fn: Callable[[], str] = _now_iso,
) -> ClassificationResult:
    if not isinstance(text, str) or not text.strip():
        return ClassificationResult(False, failure_reason="empty_or_non_text_proposal")

    ordered_taxonomy = tuple(taxonomy)
    outside_closed_set = sorted(set(ordered_taxonomy) - set(CLOSED_PROPOSAL_TAXONOMY))
    if outside_closed_set:
        return ClassificationResult(
            False,
            failure_reason=f"taxonomy_outside_closed_set:{','.join(outside_closed_set)}",
        )

    hits = _keyword_hits(text, ordered_taxonomy, keyword_map or DEFAULT_KEYWORD_MAP)
    matched = [proposal_class for proposal_class in ordered_taxonomy if proposal_class in hits]
    if not matched:
        return ClassificationResult(False, failure_reason="no_taxonomy_class_matched")

    total = sum(hits.values())
    primary = max(matched, key=lambda proposal_class: (hits[proposal_class], -ordered_taxonomy.index(proposal_class)))
    confidence = hits[primary] / total if total else 0.0
    if confidence < confidence_threshold:
        return ClassificationResult(
            False,
            failure_reason=f"classifier_confidence_below_threshold:{confidence:.4f}",
        )

    return ClassificationResult(
        True,
        ProposalClassification(
            proposal_classes=tuple(matched),
            primary_class=primary,
            classifier_confidence=round(confidence, 4),
            classifier_version=classifier_version,
            classified_at=now_fn(),
        ),
    )


def assign_critical_domain_relevance(
    votes: Iterable[Vote],
    proposal_classes: Iterable[str],
    domain_map: Dict[str, list[str]],
) -> None:
    classes = set(proposal_classes)
    for vote in votes:
        vote.critical_domain_relevance = bool(set(domain_map.get(vote.node_key, [])) & classes)
