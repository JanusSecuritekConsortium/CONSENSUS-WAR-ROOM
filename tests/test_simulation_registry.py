from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.simulation.registry import SCENARIO_TYPES, default_registry


def test_simulation_registry_exposes_canonical_types() -> None:
    registry = default_registry()
    assert set(SCENARIO_TYPES).issubset(set(registry.list_types()))
    registry.validate_type("geopolitical_conflict")
    try:
        registry.validate_type("invented_forecast")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown scenario type accepted")


if __name__ == "__main__":
    test_simulation_registry_exposes_canonical_types()
    print("test_simulation_registry PASS")
