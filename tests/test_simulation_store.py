from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.simulation.store import create_stored_scenario, get_simulation_status, list_recent_scenarios


def test_simulation_store_tolerates_corrupt_jsonl() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "simulation_history.jsonl"
        path.write_text("{corrupt}\n", encoding="utf-8")
        scenario = create_stored_scenario(
            path=path,
            title="Stored",
            description="Scaffold",
            scenario_type="cyber_incident",
        )
        assert list_recent_scenarios(path=path)[0]["scenario_id"] == scenario.scenario_id
        status = get_simulation_status(path)
        assert status["scenario_count"] == 1
        assert status["latest_branch_count"] == 1


if __name__ == "__main__":
    test_simulation_store_tolerates_corrupt_jsonl()
    print("test_simulation_store PASS")
