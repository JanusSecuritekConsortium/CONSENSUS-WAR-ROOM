from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BootProfile:
    key: str
    theme_key: str
    headline: str
    boot_lines: List[str]
    status_lines: List[str]
    sample_phrase: str


GLOBAL_BOOT_MARKERS = [
    "CONSENSUS TACTICAL BIOS",
    "WAR ROOM INIT PROTOCOL",
    "POST: Quantum Core Check",
    "RATIONALIS [Logic Engine]",
    "AETERNUM [Temporal Core]",
    "BELLATOR [Tactical Matrix]",
    "Neural Networks: Calibrated",
    "TTS Engine: GLaDOS Core",
    "Proposal Watcher: Armed",
    "Memory Store: Mounted",
    "CONSENSUS SYSTEM READY",
]


BOOT_PROFILES: Dict[str, BootProfile] = {
    "military_boot": BootProfile(
        key="military_boot",
        theme_key="military",
        headline="COMMAND-LINE DIAGNOSTIC BOOT",
        boot_lines=[
            "CONSENSUS TACTICAL BIOS: tactical decision matrix powered",
            "WAR ROOM INIT PROTOCOL: EXCOMM command layer online",
            "POST: Quantum Core Check",
            "COMMS: independent monolith channels linked",
            "MONOLITH LINK: quorum and confidence gates calibrated",
            "COMMAND BUFFER: standing by for proposal",
        ],
        status_lines=["SYSTEM CHECK", "COMMS", "MONOLITH LINK", "TACTICAL BUS"],
        sample_phrase="GREEN TACTICAL LOADING BAR",
    ),
    "eva_boot": BootProfile(
        key="eva_boot",
        theme_key="eva",
        headline="MAGI SYNCHRONIZATION BOOT",
        boot_lines=[
            "MAGI LINK ESTABLISHED: personality lattice synchronized",
            "SYNCHRONIZATION RATE: CASPER/BALTHASAR/MELCHIOR nominal",
            "PATTERN ANALYSIS: contradiction alarms armed",
            "HUMAN INTERLOCK: authorization layer online",
        ],
        status_lines=["MAGI LINK", "SYNCHRONIZATION RATE", "PATTERN ANALYSIS", "INTERLOCK BUS"],
        sample_phrase="MAGI-LINK SYNCHRONIZATION",
    ),
    "nerv_boot": BootProfile(
        key="nerv_boot",
        theme_key="nerv",
        headline="NERV MAGI INTERLOCK BOOT",
        boot_lines=[
            "MAGI LINK ESTABLISHED: NERV command layer armed",
            "SYNCHRONIZATION RATE: tribunal channels converging",
            "PATTERN ANALYSIS: proposal route locked",
            "ALERT ACCENTS: orange/red warning bus active",
        ],
        status_lines=["MAGI LINK", "SYNCHRONIZATION RATE", "PATTERN ANALYSIS", "INTERLOCK BUS"],
        sample_phrase="NERV MAGI-LINK INTERLOCK",
    ),
    "wh40k_boot": BootProfile(
        key="wh40k_boot",
        theme_key="wh40k",
        headline="IMPERIAL GOTHIC TERMINAL RITUAL",
        boot_lines=[
            "DATE REF: 0918015.M03",
            "CHRONO-STAMP: 0918015.M03",
            "NOOSPHERIC TIME INDEX: 0918015.M03",
            "MACHINE SPIRIT AWAKENED: logic cogitator stirred",
            "COGITATOR ONLINE: tithe ledger sealed",
            "SANCTION PROTOCOL: tactica engine blessed",
            "ARCHIVE DATE: 0918015.M03",
            "RITE COMPLETE: sanctioned proposal channel open",
        ],
        status_lines=[
            "DATE REF: 0918015.M03",
            "MACHINE SPIRIT AWAKENED",
            "COGITATOR ONLINE",
            "NOOSPHERIC TIME INDEX: 0918015.M03",
            "SANCTION PROTOCOL",
            "RITE COMPLETE",
        ],
        sample_phrase="COGITATOR RITE AND LITANY",
    ),
    "helldivers_boot": BootProfile(
        key="helldivers_boot",
        theme_key="helldivers",
        headline="SUPER EARTH COMMAND AUTHORIZATION",
        boot_lines=[
            "DEMOCRATIC AUTHORIZATION: deliberation permit granted",
            "LIBERTY LOGIC: civic review online",
            "REQUISITION ACCOUNTING: supply audit synchronized",
            "STRATAGEM SAFETY: tactical review armed",
        ],
        status_lines=["DEMOCRATIC AUTHORIZATION", "LIBERTY LOGIC", "REQUISITION ACCOUNTING", "STRATAGEM SAFETY"],
        sample_phrase="LIBERTY AND DEMOCRACY BAR",
    ),
    "arasaka_boot": BootProfile(
        key="arasaka_boot",
        theme_key="arasaka",
        headline="CORPORATE BLACK/RED SECURITY BOOT",
        boot_lines=[
            "SECURITY CLEARANCE: executive channel verified",
            "COUNTERINTELLIGENCE GRID: exposure scan engaged",
            "CORPORATE NODE ONLINE: capital ledger locked",
            "BOARD VERDICT CHANNEL: standing by",
        ],
        status_lines=["SECURITY CLEARANCE", "COUNTERINTELLIGENCE GRID", "CORPORATE NODE ONLINE", "BOARD VERDICT CHANNEL"],
        sample_phrase="CORPORATE CLEARANCE GRID",
    ),
    "janus_boot": BootProfile(
        key="janus_boot",
        theme_key="janus",
        headline="DUAL-FACE INTELLIGENCE BOOT",
        boot_lines=[
            "DUAL CHANNEL OPEN: present and future fronts linked",
            "ANALYTIC MIRROR ONLINE: counterpart review active",
            "COUNTERPART SYNC: tactical and strategic deltas aligned",
            "REVERSIBILITY CHECK: decision path buffered",
        ],
        status_lines=["DUAL CHANNEL OPEN", "ANALYTIC MIRROR ONLINE", "COUNTERPART SYNC", "REVERSIBILITY CHECK"],
        sample_phrase="DUAL-FRONT MIRROR SYNC",
    ),
}


def get_boot_profile(profile_id: str) -> BootProfile:
    try:
        return BOOT_PROFILES[profile_id]
    except KeyError as exc:
        raise RuntimeError(f"Unknown boot profile: {profile_id}") from exc
