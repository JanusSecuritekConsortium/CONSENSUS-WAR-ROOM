from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.simulation.branches import create_initial_branch, generate_child_branch


def test_branch_generation_tracks_parent_and_divergence() -> None:
    root = create_initial_branch("sim_test")
    child = generate_child_branch(root, assumptions_delta={"sanctions": "increase"}, escalation_flags=["economic"])
    assert child.parent_branch_id == root.branch_id
    assert child.divergence_index == root.divergence_index + 1
    assert child.risk_score > root.risk_score


if __name__ == "__main__":
    test_branch_generation_tracks_parent_and_divergence()
    print("test_branch_generation PASS")
