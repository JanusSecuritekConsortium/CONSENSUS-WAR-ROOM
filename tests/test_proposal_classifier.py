"""Keyword classifier: real questions in English or Spanish are classified; gibberish still fails closed."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.voting.classifier import classify_proposal
from core.voting.rules import ConsensusRules

RULES = ConsensusRules()


def classify(text, threshold=None):
    return classify_proposal(text, taxonomy=RULES.proposal_taxonomy,
                             confidence_threshold=RULES.classification_confidence_threshold if threshold is None else threshold)


class ProposalClassifierTest(unittest.TestCase):
    def test_spanish_question_with_accents_is_classified(self):
        result = classify("¿Debo mover las copias de seguridad al disco nuevo?")
        self.assertTrue(result.ok, result.failure_reason)
        self.assertEqual(result.classification.proposal_classes, ("analysis", "security", "operations"))

    def test_everyday_decision_is_deliberated(self):
        self.assertTrue(classify("¿Me conviene cambiar de trabajo?").ok)
        self.assertEqual(classify("Should I buy a new GPU this month?").classification.primary_class, "finance")

    def test_broad_proposal_is_not_penalised_for_spanning_domains(self):
        result = classify("Should I invest in the stock market given the risk?")
        self.assertTrue(result.ok, result.failure_reason)
        self.assertEqual(set(result.classification.proposal_classes), {"analysis", "finance", "economics", "risk"})

    def test_specific_class_wins_over_decision_wording(self):
        self.assertEqual(classify("Geopolitical analysis request").classification.primary_class, "geopolitics")
        self.assertEqual(classify("analysis review validation proposal").classification.primary_class, "analysis")

    def test_gibberish_still_fails_closed(self):
        self.assertEqual(classify("xyzzy plugh frobnicate").failure_reason, "no_taxonomy_class_matched")

    def test_stricter_threshold_needs_more_evidence(self):
        self.assertFalse(classify("runtime integration vote", threshold=0.75).ok)
        self.assertTrue(classify("runtime integration vote").ok)



class BoldBellatorDomainTest(unittest.TestCase):
    """BELLATOR is the Growth Core; security and risk keep two guardians, BELLATOR and RATIONALIS."""

    def test_growth_questions_are_classified_in_both_languages(self):
        for text in ("Should we expand into Asia and seize the opportunity?",
                     "¿Aprovechamos la oportunidad para crecer y lanzar el producto?"):
            result = classify(text)
            self.assertTrue(result.ok, result.failure_reason)
            self.assertIn("growth", result.classification.proposal_classes)

    def test_every_class_still_has_a_guardian(self):
        from config.runtime import RuntimeConfig
        for domain_map in (RULES.monolith_domain_map, RuntimeConfig().monolith_domain_map):
            covered = {domain for domains in domain_map.values() for domain in domains}
            self.assertEqual(covered, set(RULES.proposal_taxonomy))
            self.assertIn("growth", domain_map["BELLATOR"])
            for guardian in ("RATIONALIS", "BELLATOR"):
                self.assertTrue({"security", "risk"} <= set(domain_map[guardian]), guardian)

    def test_security_critical_risk_counts_for_both_guardians(self):
        from core.models import Vote, VoteValue
        from core.voting.classifier import assign_critical_domain_relevance
        votes = [Vote("RATIONALIS", "Logic", VoteValue.DENY, 0.9, "breach", critical_risk=True),
                 Vote("BELLATOR", "Growth", VoteValue.DENY, 0.8, "unsurvivable", critical_risk=True),
                 Vote("AETERNUM", "Finance", VoteValue.APPROVE, 0.8, "fine")]
        assign_critical_domain_relevance(votes, ["security"], RULES.monolith_domain_map)
        self.assertEqual([vote.critical_domain_relevance for vote in votes], [True, True, False])
        assign_critical_domain_relevance(votes, ["growth"], RULES.monolith_domain_map)
        self.assertEqual([vote.critical_domain_relevance for vote in votes], [False, True, False])


if __name__ == "__main__":
    unittest.main()
