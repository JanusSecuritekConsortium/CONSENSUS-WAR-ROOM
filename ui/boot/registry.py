from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping, Sequence

from ui.themes.catalog import resolve_theme_key


BASE_DETECTED_DEVICES: tuple[str, ...] = (
    "Consensus Neural Thread v9.12",
    "Memory Alignment Controller",
    "Quantum Entanglement Buffers",
    "Neural Processor",
    "Quantum Cryptographic Module",
    "Hyperlane Storage",
    "Secure Tunnel Port 7851",
    "Proposal Watcher",
    "Memory Store",
    "Consensus Integrity Engine",
    "Strategic Simulation Core",
    "Tribunal Session Bus",
    "Behavioral Drift Monitor",
    "Runtime Consensus Cache",
    "Forecast Vector Lattice",
    "Autonomous Briefing Engine",
    "Cognitive Conflict Resolver",
    "Neural Arbitration Matrix",
    "Tactical Dossier Store",
    "Signal Correlation Layer",
    "Operator Authentication Relay",
    "Geopolitical Event Buffer",
    "Strategic Scenario Engine",
)

BASE_POST_CHECKS: tuple[str, ...] = (
    "[OK] Core Integrity",
    "[OK] Theme Catalog",
    "[OK] Static Logos",
    "[OK] Agent Registry",
    "[OK] Msty Runtime Adapter",
    "[OK] Strategic Forecast Registry",
    "[OK] Branch Simulation Engine",
    "[OK] Tribunal Synchronization Layer",
    "[OK] Runtime Telemetry",
    "[OK] Tactical Memory Store",
    "[OK] Dossier Export Layer",
    "[OK] Monolith Consensus Mesh",
    "[OK] Operator Command Bus",
    "[OK] Scenario Persistence Layer",
    "[OK] Proposal Lifecycle Registry",
    "[OK] Shadow Context Layer",
    "[OK] Voice Carrier Modulator",
    "[OK] Verdict Transmission Bus",
)

BASE_RARE_POST_CHECKS: tuple[str, ...] = (
    "[WARN] Forecast Drift Detected",
    "[WARN] Consensus Variance Elevated",
    "[SYNC] Tribunal Mesh Stabilized",
)


@dataclass(frozen=True)
class ThemeBootRegistry:
    theme_key: str
    devices: tuple[str, ...]
    post_checks: tuple[str, ...]
    rare_post_checks: tuple[str, ...]


def _registry(devices: Sequence[str], post_checks: Sequence[str], rare: Sequence[str] = ()) -> ThemeBootRegistry:
    # Placeholder theme_key is replaced while building the public mapping.
    return ThemeBootRegistry("", tuple(devices), tuple(post_checks), tuple(rare))


_THEME_SPECIFIC: Mapping[str, ThemeBootRegistry] = {
    "military": _registry(
        (
            "EXCOMM Tactical Display Engine",
            "Strategic Command SATCOM Relay",
            "THREATCON Chain-of-Command Bus",
            "Mission-Critical Systems",
            "DEFCON Status Monitor",
            "Health Monitoring Uplink",
        ),
        (
            "[OK] Command Runtime",
            "[OK] EXCOMM Strategic Command",
            "[OK] SATCOM Threat Relay",
            "[OK] Chain of Command",
            "[OK] DEFCON Status Monitor",
            "[OK] Mission Board",
        ),
        ("[SYNC] Command Mesh Stabilized",),
    ),
    "eva": _registry(
        (
            "MAGI Pattern Analysis Accelerator",
            "CASPER Logic Interface",
            "BALTHASAR Forecast Node",
            "MELCHIOR Defense Interlock",
            "CENTRAL DOGMA Link",
            "LCL Buffer Synchronizer",
            "Cortical Bridge",
            "Judgement Gate",
        ),
        (
            "[OK] MAGI Runtime",
            "[OK] CENTRAL DOGMA Link",
            "[OK] CASPER Logic Node",
            "[OK] BALTHASAR Forecast Node",
            "[OK] MELCHIOR Tactical Node",
            "[OK] LCL Buffer",
            "[OK] Judgement Gate",
        ),
        ("[SYNC] MAGI Harmonization Stable",),
    ),
    "nerv": _registry(
        (
            "MAGI Pattern Analysis Accelerator",
            "NERV Tactical Interlock",
            "CASPER Scientific Analysis Core",
            "BALTHASAR Maternal Intuition Core",
            "MELCHIOR Paternal Instinct Core",
            "CENTRAL DOGMA Link",
            "LCL Buffer Synchronizer",
        ),
        (
            "[OK] MAGI Runtime",
            "[OK] NERV Command Layer",
            "[OK] CENTRAL DOGMA Link",
            "[OK] MAGI Personality Lattice",
            "[OK] Pattern Blue Monitor",
        ),
        ("[SYNC] NERV MAGI Interlock Stable",),
    ),
    "wh40k": _registry(
        (
            "Noospheric Cogitator Display Engine",
            "Machine Spirit Litany Buffer",
            "Tactica Imperialis Data-Vault",
            "Holy Synod Authorization Seal",
            "Omnissiah Chrono-Rite Index",
            "Servitor Binding Channel",
        ),
        (
            "[OK] Machine Spirit Litany",
            "[OK] Cogitator Runtime",
            "[OK] Noospheric Link",
            "[OK] Tactica Imperialis",
            "[OK] Holy Synod Seal",
            "[OK] Servitor Binding",
        ),
        ("[SYNC] Machine Spirit Placated",),
    ),
    "helldivers": _registry(
        (
            "Super Earth Tactical Display Engine",
            "Managed Democracy Authorization Line",
            "LIBERTYCOM Patriot Relay",
            "Ministry of Truth Oversight Port",
            "Freedom Forecasting System",
            "Stratagem Safety Grid",
        ),
        (
            "[OK] Democracy Runtime",
            "[OK] SUPER EARTH Command",
            "[OK] Managed Democracy Protocol",
            "[OK] LIBERTYCOM Relay",
            "[OK] Patriotic Oversight",
            "[OK] Voice of Freedom",
        ),
        ("[SYNC] Liberty Signal Confirmed",),
    ),
    "arasaka": _registry(
        (
            "Arasaka Black/Red Security Display Engine",
            "Executive Secure Channel",
            "Corporate Oversight Grid",
            "BLACKWALL Counter-Intrusion Gate",
            "Due-Diligence Logic Bus",
            "Asset Continuity Table",
        ),
        (
            "[OK] Corporate Runtime",
            "[OK] Executive Secure Channel",
            "[OK] Corporate Oversight",
            "[OK] BLACKWALL Counter-Intrusion",
            "[OK] Due-Diligence Grid",
            "[OK] Asset Continuity",
        ),
        ("[SYNC] Executive Mesh Stabilized",),
    ),
    "janus": _registry(
        (
            "Janus Mirror Channel Display Engine",
            "Dual-Vector Analysis Relay",
            "Bifurcated Tribunal Bus",
            "Mirrored Consensus Cache",
            "Twin-Core Synchronization Gate",
            "Parallax Drift Monitor",
        ),
        (
            "[OK] Mirror Runtime",
            "[OK] Dual-Vector Analysis",
            "[OK] Bifurcated Tribunal Bus",
            "[OK] Mirrored Consensus",
            "[OK] Twin-Core Synchronization",
            "[OK] Parallax Drift Monitor",
        ),
        ("[SYNC] Twin-Core Synchronization Stable",),
    ),
}

BOOT_PHRASE_REGISTRY: Mapping[str, ThemeBootRegistry] = {
    key: ThemeBootRegistry(key, value.devices, value.post_checks, value.rare_post_checks)
    for key, value in _THEME_SPECIFIC.items()
}


def boot_registry_for_theme(theme_id: str) -> ThemeBootRegistry:
    return BOOT_PHRASE_REGISTRY[resolve_theme_key(theme_id)]


def _unique_stable(items: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return tuple(result)


def _select_unique(pool: Sequence[str], count: int, rng: random.Random) -> tuple[str, ...]:
    unique = list(_unique_stable(pool))
    if count >= len(unique):
        return tuple(unique)
    selected: list[str] = []
    remaining = unique[:]
    while remaining and len(selected) < count:
        index = rng.randrange(len(remaining))
        selected.append(remaining.pop(index))
    return tuple(selected)


def select_detected_devices(theme_id: str, rng: random.Random, count: int = 10) -> tuple[str, ...]:
    registry = boot_registry_for_theme(theme_id)
    base_count = min(6, count)
    common = _select_unique(BASE_DETECTED_DEVICES, base_count, rng)
    themed = _select_unique(registry.devices, max(0, count - len(common)), rng)
    return _unique_stable((*common, *themed))


def select_post_checks(theme_id: str, rng: random.Random, count: int = 9, include_rare: bool = False) -> tuple[str, ...]:
    registry = boot_registry_for_theme(theme_id)
    base_count = min(5, count)
    common = _select_unique(BASE_POST_CHECKS, base_count, rng)
    themed = _select_unique(registry.post_checks, max(0, count - len(common)), rng)
    rare = _select_unique((*BASE_RARE_POST_CHECKS, *registry.rare_post_checks), 1, rng) if include_rare else ()
    return _unique_stable((*common, *themed, *rare))

