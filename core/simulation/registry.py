from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


SCENARIO_TYPES = (
    "geopolitical_conflict",
    "economic_crisis",
    "sanctions_pressure",
    "alliance_shift",
    "regime_instability",
    "military_escalation",
    "cyber_incident",
    "strategic_forecast",
)


@dataclass(frozen=True)
class ScenarioTypeDefinition:
    scenario_type: str
    title: str
    default_confidence_model: str = "deterministic_scaffold_v1"


class SimulationRegistry:
    def __init__(self, definitions: List[ScenarioTypeDefinition]) -> None:
        self._definitions: Dict[str, ScenarioTypeDefinition] = {
            definition.scenario_type: definition for definition in definitions
        }

    def list_types(self) -> List[str]:
        return list(self._definitions)

    def get(self, scenario_type: str) -> ScenarioTypeDefinition:
        try:
            return self._definitions[scenario_type]
        except KeyError as exc:
            raise KeyError(f"Unknown simulation scenario type: {scenario_type}") from exc

    def validate_type(self, scenario_type: str) -> None:
        self.get(scenario_type)


def default_registry() -> SimulationRegistry:
    return SimulationRegistry(
        [
            ScenarioTypeDefinition("geopolitical_conflict", "Geopolitical Conflict"),
            ScenarioTypeDefinition("economic_crisis", "Economic Crisis"),
            ScenarioTypeDefinition("sanctions_pressure", "Sanctions Pressure"),
            ScenarioTypeDefinition("alliance_shift", "Alliance Shift"),
            ScenarioTypeDefinition("regime_instability", "Regime Instability"),
            ScenarioTypeDefinition("military_escalation", "Military Escalation"),
            ScenarioTypeDefinition("cyber_incident", "Cyber Incident"),
            ScenarioTypeDefinition("strategic_forecast", "Strategic Forecast"),
        ]
    )
