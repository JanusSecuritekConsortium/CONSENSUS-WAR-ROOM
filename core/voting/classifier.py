from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, Optional

from core.models import Vote


DEFAULT_KEYWORD_MAP: Dict[str, tuple[str, ...]] = {
    # English stems, then Spanish; matched after accents are removed ("análisis" -> "analisis").
    "logic": ("logic", "reason", "consisten", "premise", "fallacy", "infer",
              "razon", "coheren", "premisa", "falacia", "deduc"),
    "governance": ("governance", "policy", "regulat", "compliance", "charter", "mandate", "legal", "contract",
                   "gobern", "politica", "normativ", "regulac", "cumplimiento", "contrato"),
    "ethics": ("ethic", "moral", "fairness", "rights", "harm", "consent",
               "etica", "justicia", "derecho", "dano", "consentim"),
    # Plain decision wording lands here, so an everyday "should I...?" is still deliberated.
    "analysis": ("analy", "evaluat", "assess", "breakdown", "diagnos", "review", "validat", "approv", "proposal", "test",
                 "should", "whether", "decide", "decision", "option", "choose", "change", "switch",
                 "analis", "evalu", "revis", "valid", "aprob", "propuesta", "prueba",
                 "deber", "debo", "debe", "decid", "elegir", "cambiar", "opin", "opcion", "conviene", "vale la pena"),
    "finance": ("financ", "budget", "cost", "revenue", "capital", "invest", "funding",
                "money", "price", "pay", "salary", "spend", "saving", "afford", "buy", "loan", "debt", "mortgage", "rent",
                "presupuest", "ingreso", "invers", "invert", "dinero", "precio", "pagar", "ahorr", "gasto",
                "sueldo", "salario", "comprar", "prestamo", "deuda", "hipoteca", "alquiler"),
    "forecasting": ("forecast", "predict", "projection", "outlook", "trend", "future",
                    "pronostic", "predic", "proyeccion", "perspectiva", "tendencia", "futuro"),
    "economics": ("econom", "market", "inflation", "supply", "demand", "gdp", "trade",
                  "mercado", "inflac", "oferta", "pib", "comercio"),
    "historical_patterns": ("histor", "precedent", "pattern", "prior", "past", "legacy",
                            "patron", "previo", "pasado", "legado"),
    "security": ("secur", "vulnerab", "threat", "breach", "attack", "exploit", "intrusion",
                 "privacy", "password", "malware", "phishing", "scam", "fraud",
                 "seguridad", "amenaza", "brecha", "ataque", "explot", "intrus", "privacidad", "contrasena",
                 "estafa", "fraude"),
    "geopolitics": ("geopolit", "nation", "sovereign", "treaty", "border", "diplom", "alliance",
                    "nacion", "soberan", "tratado", "frontera", "alianza"),
    "risk": ("risk", "downside", "hazard", "exposure", "danger", "liabilit",
             "riesgo", "desventaja", "peligro", "exposicion", "responsabilid"),
    "operations": ("operation", "logistic", "deploy", "execution", "ops", "rollout", "runtime",
                   "migrat", "install", "upgrade", "backup",
                   "operac", "despleg", "desplieg", "ejecuc", "implement", "migra", "instal",
                   "mover", "mudanza"),
    "growth": ("growth", "grow", "expan", "opportunit", "scale", "scaling", "launch", "advantage", "ambiti",
               "momentum", "seize", "capture", "conquer",
               "crecim", "crecer", "oportunidad", "escalar", "lanzar", "lanzamiento", "ventaja", "ambici",
               "aprovechar", "conquist"),
}

# Decision wording says a choice is being made, not what it is about; a specific class wins when one matches.
GENERIC_CLASS = "analysis"

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
    lowered = "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))
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
    classifier_version: str = "1.1.0",
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

    specific = {proposal_class: count for proposal_class, count in hits.items() if proposal_class != GENERIC_CLASS}
    ranked = specific or hits
    primary = max(ranked, key=lambda proposal_class: (ranked[proposal_class], -ordered_taxonomy.index(proposal_class)))
    # Confidence is how much taxonomy evidence the text carries (1 hit 0.67, 2 hits 0.8, 3 hits 0.86), so a
    # proposal spanning several domains, as tribunal questions usually do, is not penalised for being broad.
    total = sum(hits.values())
    confidence = total / (total + 0.5)
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
