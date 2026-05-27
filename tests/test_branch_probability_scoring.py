from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.simulation.branches import evaluate_branch_probability, score_branch_risk


def test_probability_and_risk_are_deterministic() -> None:
    delta = {"trigger": "threshold"}
    assert evaluate_branch_probability(delta, depth=2) == evaluate_branch_probability(delta, depth=2)
    assert evaluate_branch_probability(delta, depth=2) < evaluate_branch_probability({}, depth=0)
    assert score_branch_risk(["military"], delta) > score_branch_risk([], {})


if __name__ == "__main__":
    test_probability_and_risk_are_deterministic()
    print("test_branch_probability_scoring PASS")
