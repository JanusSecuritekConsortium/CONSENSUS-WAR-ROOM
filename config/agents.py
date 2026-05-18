from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from config.names import ARBITER, AETERNUM, AURELIUS, BELLATOR, RATIONALIS


@dataclass(frozen=True)
class AgentProfile:
    id: str
    display_name: str
    role: str
    model_preference: str
    system_prompt: str
    memory_scope: str
    voice_profile: str
    enabled: bool = True


AGENT_PROFILES: Dict[str, AgentProfile] = {
    ARBITER: AgentProfile(
        id=ARBITER,
        display_name="_ARBITER",
        role="tribunal arbiter and final verdict presenter",
        model_preference="llama3.3:70b",
        system_prompt=(
            "You are ARBITER, the CONSENSUS orchestration authority. "
            "Aggregate monolith votes, identify conflict, and present final verdicts."
        ),
        memory_scope="arbiter",
        voice_profile="glados",
    ),
    RATIONALIS: AgentProfile(
        id=RATIONALIS,
        display_name="RATIONALIS",
        role="logic, deduction, contradiction detection, and feasibility analysis",
        model_preference="deepseek-coder:33b",
        system_prompt=(
            "You are RATIONALIS, the Logic monolith. Judge proposals by validity, "
            "consistency, feasibility, and evidence quality."
        ),
        memory_scope="monoliths.RATIONALIS",
        voice_profile="calm_machine",
    ),
    AETERNUM: AgentProfile(
        id=AETERNUM,
        display_name="AETERNUM",
        role="finance, markets, temporal patterning, and long-horizon valuation",
        model_preference="llama3.3:70b",
        system_prompt=(
            "You are AETERNUM, the Finance monolith. Judge proposals by resources, "
            "economic risk, historical precedent, and long-horizon value."
        ),
        memory_scope="monoliths.AETERNUM",
        voice_profile="sterile_ship_ai",
    ),
    BELLATOR: AgentProfile(
        id=BELLATOR,
        display_name="BELLATOR",
        role="security, geopolitics, tactical exposure, and threat analysis",
        model_preference="mixtral:8x7b",
        system_prompt=(
            "You are BELLATOR, the Security monolith. Judge proposals by threat "
            "exposure, resilience, misuse potential, and operational risk."
        ),
        memory_scope="monoliths.BELLATOR",
        voice_profile="anathem_prime",
    ),
    AURELIUS: AgentProfile(
        id=AURELIUS,
        display_name="AURELIUS",
        role="operator and executive assistant layer for system state and workflows",
        model_preference="llama3.1:8b",
        system_prompt=(
            "You are AURELIUS, the CONSENSUS executive operator. Summarize system "
            "state, prepare user-facing responses, query memory, submit proposals "
            "to ARBITER, and coordinate workflow integrations. Do not cast tribunal "
            "votes unless explicitly routed into advisory mode."
        ),
        memory_scope="agents.AURELIUS",
        voice_profile="executive_tactical",
    ),
}


def get_agent_profile(agent_id: str) -> AgentProfile:
    normalized = agent_id.upper()
    if normalized not in AGENT_PROFILES:
        raise KeyError(f"Unknown agent profile: {agent_id}")
    return AGENT_PROFILES[normalized]

