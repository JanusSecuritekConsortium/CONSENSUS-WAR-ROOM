from __future__ import annotations

import argparse
import functools
import os
import platform
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_LAST_PATCH_DATE, SYSTEM_VERSION
from ui.animations.bios_boot import (
    BootHardwareSnapshot,
    _bios_header_lines,
    _boot_color_values,
    _provider_post_line,
    _theme_runtime_label,
    _theme_boot_logo_text,
    capture_boot_hardware_snapshot,
    hardware_diagnostic_rows,
)
from ui.animations.loading import format_loading_bar, get_loading_style
from ui.boot.registry import boot_registry_for_theme
from ui.themes.catalog import THEMES, resolve_theme_key


AUTHOR_LINE = "Chief Architect: Erhardt Von Grupten Mundt"
ORGANIZATION_LINE = "Janus Securitek Consortium / CONSENSUS Tactical Systems"
DEFAULT_WIDTH = 100
MIN_PREVIEW_WIDTH = 64
COMPACT_WIDTH = 96
SUPPORTED_THEME_KEYS = ("eva", "arasaka", "military", "wh40k", "helldivers", "janus")

SPEEDS = {
    # character delay, completed-line delay, centered-logo hold
    "fast": (0.0010, 0.012, 0.40),
    "normal": (0.0030, 0.030, 0.95),
    "slow": (0.0060, 0.060, 1.50),
}
TARGET_BOOT_SECONDS = {"fast": 7.0, "normal": 13.0, "slow": 21.0}
MIN_RENDER_SLEEP = 0.016

BASE_CONFIGURATION_ROWS: Sequence[tuple[str, str, str, str]] = (
    ("0D0E0", "SYS", "5296", "kernel"),
    ("0D22C", "SYS", "2416", "terminal_driver"),
    ("0D2C4", "2081", "16384", "consensus_bus"),
    ("0D6C5", "DBFE", "21392", "<free>"),
    ("0DE02", "E000", "8160", "<free>"),
    ("00586", "SYS", "2144", "memory_alignment"),
    ("0060D", "SYS", "3968", "forecast_vector"),
    ("00706", "SYS", "3312", "judgement_gate"),
)

EVA_SUBSYSTEM_ROWS: Sequence[tuple[str, str, str, str]] = (
    ("MELCHIOR-1", "LINK", "99.98%", "ONLINE"),
    ("BALTHASAR-2", "LINK", "99.96%", "ONLINE"),
    ("CASPER-3", "LINK", "99.99%", "ONLINE"),
    ("RATIONALIS", "LOGIC CORE", "NOMINAL", "ONLINE"),
    ("AETERNUM", "TEMPORAL CORE", "NOMINAL", "ONLINE"),
    ("BELLATOR", "TACTICAL MATRIX", "NOMINAL", "ONLINE"),
    ("ARBITER", "QUORUM CONTROL", "LOCKED", "ONLINE"),
)

SUMMARY_LINES = {
    "eva": "PATTERN ANALYSIS: BLUE    CONSENSUS INTEGRITY: 99.97%    HUMAN INTERLOCK: ARMED",
    "arasaka": "BLACKWALL: SECURED    CLEARANCE INTEGRITY: 99.94%    EXECUTIVE CHANNEL: ARMED",
    "military": "THREATCON: GREEN    COMMAND INTEGRITY: 99.91%    AUTHORIZATION BUS: ARMED",
    "wh40k": "MACHINE SPIRIT: PURE    NOOSPHERIC INTEGRITY: 99.88%    SANCTION SEAL: BLESSED",
    "helldivers": "LIBERTY INDEX: MAXIMUM    DEMOCRACY INTEGRITY: 99.93%    STRATAGEM BUS: ARMED",
    "janus": "MIRROR STATE: ALIGNED    DUAL-CHANNEL INTEGRITY: 99.95%    COUNTERPART GATE: ARMED",
}

READY_LINES = {
    "eva": "MAGI CONSENSUS ARRAY READY",
    "arasaka": "ARASAKA EXECUTIVE GRID READY",
    "military": "EXCOMM WAR ROOM READY",
    "wh40k": "IMPERIAL COGITATOR AWAKENED",
    "helldivers": "MANAGED DEMOCRACY INTERFACE READY",
    "janus": "JANUS MIRROR CHANNEL READY",
}

LOADING_BAR_LABELS = {
    "eva": "MAGI-LINK",
    "arasaka": "SECURITY CLEARANCE",
    "military": "TACTICAL",
    "wh40k": "MACHINE-SPIRIT PURITY",
    "helldivers": "DEMOCRATIC AUTHORIZATION",
    "janus": "DUAL-CHANNEL SYNC",
}

HANDOFF_LINES = {
    "eva": "TRANSFERRING CONTROL TO MAGI WAR ROOM...",
    "arasaka": "EXECUTIVE SESSION AUTHORIZED — OPENING WAR ROOM...",
    "military": "BOOT DEVICE ACCEPTED — EXECUTING COMMAND INTERFACE...",
    "wh40k": "THE DATA THRONE AWAITS — ENTER THE WAR ROOM...",
    "helldivers": "DEPLOYING MANAGED DEMOCRACY — OPENING WAR ROOM...",
    "janus": "BOTH FACES AGREE — OPENING WAR ROOM...",
}


@dataclass(frozen=True)
class EvaPalette:
    """Terminal palette fields retained for compatibility with the EVA prototype tests."""

    orange: str = ""  # theme primary
    red: str = ""  # theme secondary
    cyan: str = ""  # theme accent
    white: str = ""  # theme text
    warning: str = ""
    reset: str = ""
    logo: str = ""
    background: str = ""
    theme_key: str = ""


@dataclass(frozen=True)
class ExtendedBootTelemetry(BootHardwareSnapshot):
    """Privacy-safe hardware identity and capacity sampled for one preview."""

    available_memory_mb: int = 0
    cpu_model: str = "PROCESSOR QUERY UNAVAILABLE"
    gpu_model: str = "DISPLAY ADAPTER QUERY UNAVAILABLE"
    os_version: str = "OPERATING SYSTEM QUERY UNAVAILABLE"
    system_drive_total_gib: float = 0.0
    system_drive_free_gib: float = 0.0


@dataclass
class PreviewControls:
    skip: bool = False
    static: bool = False
    extended: bool = False


def _default_patch_date() -> str:
    return SYSTEM_LAST_PATCH_DATE


def _clean_hardware_label(value: object, fallback: str, limit: int = 58) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit] if text else fallback


@functools.lru_cache(maxsize=1)
def _cpu_model() -> str:
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                return _clean_hardware_label(value, "WINDOWS PROCESSOR")
        except (OSError, ImportError):
            pass
    return _clean_hardware_label(
        platform.processor() or platform.machine(),
        "PROCESSOR QUERY UNAVAILABLE",
    )


@functools.lru_cache(maxsize=1)
def _gpu_model() -> str:
    if os.name == "nt":
        try:
            import winreg

            video_path = r"SYSTEM\CurrentControlSet\Control\Video"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, video_path) as video_key:
                for guid_index in range(winreg.QueryInfoKey(video_key)[0]):
                    guid = winreg.EnumKey(video_key, guid_index)
                    try:
                        with winreg.OpenKey(video_key, rf"{guid}\0000") as adapter_key:
                            value, _ = winreg.QueryValueEx(adapter_key, "DriverDesc")
                    except OSError:
                        continue
                    label = _clean_hardware_label(value, "")
                    if label and "basic display" not in label.lower():
                        return label
        except (OSError, ImportError):
            pass
    return "DISPLAY ADAPTER QUERY UNAVAILABLE"


def _available_memory_mb(total_memory_mb: int) -> int:
    try:
        import psutil  # type: ignore

        return max(1, round(psutil.virtual_memory().available / (1024**2)))
    except Exception:
        return total_memory_mb


def capture_extended_boot_telemetry() -> ExtendedBootTelemetry:
    base = capture_boot_hardware_snapshot()
    system_root = Path(os.environ.get("SystemDrive", Path.home().anchor or "C:"))
    if not str(system_root).endswith(("\\", "/")):
        system_root = Path(f"{system_root}\\")
    try:
        drive = shutil.disk_usage(system_root)
        total_gib = drive.total / (1024**3)
        free_gib = drive.free / (1024**3)
    except OSError:
        total_gib = 0.0
        free_gib = 0.0
    os_label = f"{platform.system()} {platform.release()} ({platform.machine()})"
    return ExtendedBootTelemetry(
        total_memory_mb=base.total_memory_mb,
        physical_cores=base.physical_cores,
        logical_threads=base.logical_threads,
        memory_fallback=base.memory_fallback,
        topology_fallback=base.topology_fallback,
        available_memory_mb=_available_memory_mb(base.total_memory_mb),
        cpu_model=_cpu_model(),
        gpu_model=_gpu_model(),
        os_version=_clean_hardware_label(os_label, "OPERATING SYSTEM QUERY UNAVAILABLE"),
        system_drive_total_gib=total_gib,
        system_drive_free_gib=free_gib,
    )


def _terminal_width(requested: int | None = None) -> int:
    if requested is not None:
        return max(MIN_PREVIEW_WIDTH, requested)
    return max(MIN_PREVIEW_WIDTH, shutil.get_terminal_size((DEFAULT_WIDTH, 30)).columns)


def _center_block(text: str, width: int) -> list[str]:
    lines = text.rstrip("\n").splitlines()
    block_width = max((len(line) for line in lines), default=0)
    pad = " " * max(0, (width - block_width) // 2)
    return [pad + line for line in lines]


def _rule(title: str, width: int) -> str:
    title_text = f" {title} "
    remaining = max(4, width - len(title_text))
    left = remaining // 2
    right = remaining - left
    return ("-" * left) + title_text + ("-" * right)


def _diagnostic_line(name: str, action: str, detail: str, status: str) -> str:
    return f"{name:<23}{action:<12}{detail:<27}{status:>10}"


def _configuration_line(addr: str, psp: str, blocks: str, size: str, owner: str) -> str:
    return f"{addr:<11}{psp:<11}{blocks:>5}{size:>11}   {owner}"


def _subsystem_line(node: str, subsystem: str, value: str, status: str) -> str:
    return f"{node:<28}{subsystem:<28}{value:>10}{status:>14}"


def _owner_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:32] or "system_component"


def _diagnostic_rows(
    theme_key: str,
    snapshot: BootHardwareSnapshot | None = None,
) -> list[tuple[str, str, str, str]]:
    theme = THEMES[theme_key]
    registry = boot_registry_for_theme(theme_key)
    runtime = registry.post_checks[0].removeprefix("[OK] ")
    active_snapshot = snapshot or capture_extended_boot_telemetry()
    rows = [
        *hardware_diagnostic_rows(active_snapshot),
        ("I/O VECTORS", "CHECK", theme.boot_profile_id.upper(), "OK"),
        ("CONSOLE DRIVERS", "CHECK", "VT-09 / UTF-8", "OK"),
        ("ROUTING TABLES", "CHECK", "12 CHANNELS", "OK"),
        ("STATUS ANALYZER", "CHECK", theme.panel_style.upper()[:24], "OK"),
        ("SECURITY INTERLOCK", "CHECK", theme.border_style.upper()[:24], "OK"),
        ("THEME RUNTIME", "CHECK", runtime.upper()[:24], "OK"),
    ]
    if isinstance(active_snapshot, ExtendedBootTelemetry):
        rows[3:3] = [
            ("MEMORY AVAILABLE", "DETECT", f"{active_snapshot.available_memory_mb:,} MB", "OK"),
            ("CPU MODEL", "DETECT", active_snapshot.cpu_model[:24], "OK"),
            ("DISPLAY ADAPTER", "DETECT", active_snapshot.gpu_model[:24], "OK"),
            ("OS RUNTIME", "DETECT", active_snapshot.os_version[:24], "OK"),
            (
                "SYSTEM DRIVE",
                "DETECT",
                f"{active_snapshot.system_drive_free_gib:.1f}/{active_snapshot.system_drive_total_gib:.1f} GiB FREE",
                "OK",
            ),
        ]
    return rows


def _configuration_rows(theme_key: str) -> list[tuple[str, str, str, str, str]]:
    owners = [row[3] for row in BASE_CONFIGURATION_ROWS[:3]]
    owners.extend(_owner_slug(device) for device in boot_registry_for_theme(theme_key).devices)
    rows: list[tuple[str, str, str, str, str]] = []
    for index, (addr, psp, size, fallback_owner) in enumerate(BASE_CONFIGURATION_ROWS):
        owner = owners[index] if index < len(owners) else fallback_owner
        rows.append((addr, psp, "1", size, owner))
    return rows


def _subsystem_rows(theme_key: str) -> list[tuple[str, str, str, str]]:
    if theme_key == "eva":
        return list(EVA_SUBSYSTEM_ROWS)
    theme = THEMES[theme_key]
    rows = [
        (labels["node"][:27], labels["core"][:27], "NOMINAL", "ONLINE")
        for labels in theme.monolith_labels.values()
    ]
    rows.append(("ARBITER", "QUORUM CONTROL", "LOCKED", "ONLINE"))
    return rows


def format_theme_loading_bar(theme_id: str, percent: int, unicode: bool = True) -> str:
    return format_loading_bar(theme_id, percent, ascii_only=not unicode)


def format_magi_loading_bar(percent: int, unicode: bool = True) -> str:
    return format_theme_loading_bar("eva", percent, unicode=unicode)


def _logo_prefix(theme_key: str, width: int) -> list[str]:
    logo = _theme_boot_logo_text(theme_key)
    if max((len(line) for line in logo.splitlines()), default=0) > width:
        title = f"[ {THEMES[theme_key].display_name.upper()} BOOT ROM ]"
        return [title.center(width), ("=" * min(width, len(title) + 12)).center(width), ""]
    return [*_center_block(logo, width), ""]


def _common_footer(theme_key: str, unicode: bool) -> list[str]:
    loading = get_loading_style(theme_key)
    return [
        "",
        loading.label,
        format_theme_loading_bar(theme_key, 100, unicode=unicode),
        READY_LINES[theme_key],
        HANDOFF_LINES[theme_key],
    ]


def _provider_runtime_line(theme_key: str, provider_status: dict[str, object]) -> str:
    line = _provider_post_line(provider_status)
    if line == "[OK] Provider Runtime":
        line = f"[OK] {_theme_runtime_label(theme_key)}"
    return line


def _themed_provider_lines(
    theme_key: str,
    provider_status: dict[str, object],
    width: int,
    unicode: bool,
) -> list[str]:
    runtime = _provider_runtime_line(theme_key, provider_status)
    if theme_key == "arasaka":
        return [_boxed_rule(width), _boxed_full(runtime, width), _boxed_rule(width)]
    if theme_key == "wh40k":
        return [_ritual_rule(width, unicode), _ritual_frame(runtime, width, unicode)]
    if theme_key == "janus":
        return [_dual_column(runtime, runtime, width)]
    if theme_key == "helldivers":
        return [f'VERIFY "{_theme_runtime_label(theme_key).upper()}": {runtime}']
    return [runtime]


def _compact_notice(theme_key: str, width: int, unicode: bool) -> list[str]:
    message = "COMPACT DISPLAY — PRESS F2 FOR EXTENDED DIAGNOSTICS"
    if theme_key == "arasaka":
        return [_boxed_rule(width), _boxed_full(message, width), _boxed_rule(width)]
    if theme_key == "wh40k":
        return [
            _ritual_rule(width, unicode),
            _ritual_frame(message, width, unicode),
            _ritual_rule(width, unicode),
        ]
    if theme_key == "helldivers":
        return ["", f"REM {message}", ""]
    if theme_key == "janus":
        return ["", _dual_column("COMPACT DISPLAY", "F2: EXTENDED DIAGNOSTICS", width), ""]
    return ["", _rule(message, width), ""]


def _fit_preview_lines(lines: Sequence[str], width: int) -> list[str]:
    return [line if len(line) <= width else line[: max(1, width - 1)] + "…" for line in lines]


def _compact_preview_lines(
    theme_key: str,
    lines: Sequence[str],
    width: int,
    unicode: bool,
) -> list[str]:
    logo_count = len(_logo_prefix(theme_key, width))
    logo = list(lines[:logo_count])
    body = list(lines[logo_count:])
    if len(body) <= 30:
        return list(lines)
    head_count = 14
    tail_count = 13
    return [
        *logo,
        *body[:head_count],
        *_compact_notice(theme_key, width, unicode),
        *body[-tail_count:],
    ]


def _build_eva_dense_dummy_lines(
    *,
    width: int,
    patch: str,
    unicode: bool,
    snapshot: ExtendedBootTelemetry,
) -> list[str]:
    theme_key = "eva"
    theme = THEMES[theme_key]
    header = _bios_header_lines(theme_key, SYSTEM_VERSION)
    lines = _logo_prefix(theme_key, width)
    lines.extend(header)
    lines.extend(
        [
            AUTHOR_LINE,
            ORGANIZATION_LINE,
            f"LAST PATCH: {patch} | BUILD: v{SYSTEM_VERSION} | MODE: HIGH",
            "",
            _rule("SYSTEM DIAGNOSTICS", width),
            _diagnostic_line("DEVICE", "STATE", "PARAMETERS", "RESULT"),
            _diagnostic_line("-" * 18, "-" * 7, "-" * 18, "-" * 6),
        ]
    )
    lines.extend(_diagnostic_line(*row) for row in _diagnostic_rows(theme_key, snapshot))
    lines.extend(
        [
            "",
            _rule("CONSENSUS SYSTEM CONFIGURATION", width),
            _configuration_line("ADDR", "PSP", "BLKS", "SIZE", "OWNER / PARAMETERS"),
            _configuration_line("-" * 5, "-" * 4, "-" * 4, "-" * 4, "-" * 18),
        ]
    )
    lines.extend(_configuration_line(*row) for row in _configuration_rows(theme_key))
    lines.extend(
        [
            "",
            _rule(theme.display_name.upper(), width),
            _subsystem_line("NODE", "SUBSYSTEM", "VALUE", "STATUS"),
            _subsystem_line("-" * 12, "-" * 14, "-" * 7, "-" * 8),
        ]
    )
    lines.extend(_subsystem_line(*row) for row in _subsystem_rows(theme_key))
    lines.extend(["", SUMMARY_LINES[theme_key], *_common_footer(theme_key, unicode)])
    return lines


def _build_military_post_dummy_lines(
    *,
    width: int,
    patch: str,
    unicode: bool,
    snapshot: ExtendedBootTelemetry,
) -> list[str]:
    theme_key = "military"
    memory_gib = snapshot.total_memory_mb / 1024
    lines = _logo_prefix(theme_key, width)
    lines.extend(
        [
            "EXCOMM TACTICAL AMIBIOS (C) 2026 JANUS SECURITEK CONSORTIUM",
            f"EXCOMM SABERTOOTH COMMAND BOARD   ACPI BIOS REVISION {SYSTEM_VERSION}",
            f"BUILD: v{SYSTEM_VERSION}   LAST PATCH: {patch}   MODE: HIGH",
            AUTHOR_LINE,
            "",
            f"CPU: {snapshot.cpu_model}",
            f"     {snapshot.physical_cores} PHYSICAL CORES / {snapshot.logical_threads} LOGICAL THREADS",
            f"TOTAL MEMORY: {snapshot.total_memory_mb:,} MB ({memory_gib:.1f} GiB USABLE)",
            f"AVAILABLE MEMORY: {snapshot.available_memory_mb:,} MB",
            f"MEMORY CHECK: {snapshot.total_memory_mb:,} MB  OK",
            f"DISPLAY ADAPTER: {snapshot.gpu_model}",
            f"OPERATING SYSTEM: {snapshot.os_version}",
            f"SYSTEM DRIVE: {snapshot.system_drive_free_gib:.1f} GiB FREE / {snapshot.system_drive_total_gib:.1f} GiB TOTAL",
            "",
            "USB DEVICES TOTAL: 1 KEYBOARD, 1 POINTER, 2 SECURE HUBS",
            "DETECTED ATA/NVME DEVICES...",
            "NVME PORT0: CONSENSUS SYSTEM VOLUME",
            "NVME PORT1: ARBITER AUDIT ARCHIVE",
            "",
            "PCI DEVICE LISTING...",
            "BUS  DEV  FUNCTION              IRQ   STATUS",
            "00   01   COMMAND BRIDGE        09    ENABLED",
            "00   04   SECURE DISPLAY        11    ENABLED",
            "01   00   TACTICAL NETWORK      10    LINKED",
            "02   00   QUORUM COPROCESSOR    12    ENABLED",
            "03   00   AUDIT ARCHIVE         14    LOCKED",
            "",
            "BOOT PRIORITY:",
            "  1. CONSENSUS SYSTEM VOLUME",
            "  2. ARBITER RECOVERY PARTITION",
            "  3. EXCOMM SECURE NETWORK",
            "",
            "INITIALIZING COMMAND DEVICES...",
            "RATIONALIS LOGIC MATRIX .............. OK",
            "AETERNUM FORECAST ARRAY .............. OK",
            "BELLATOR TACTICAL GRID ............... OK",
            "ARBITER QUORUM CONTROLLER ............ OK",
            "COMMAND AUTHORIZATION BUS ............ OK",
            "TACTICAL NETWORK HANDSHAKE ........... OK",
            "",
            SUMMARY_LINES[theme_key],
            "",
            "PRESS DEL TO ENTER EXCOMM SETUP",
            "BOOTING CONSENSUS WAR ROOM...",
            *_common_footer(theme_key, unicode),
        ]
    )
    return lines


def _boxed_full(text: str, width: int) -> str:
    inner = max(1, width - 2)
    return "|" + text[:inner].center(inner) + "|"


def _boxed_pair(left: str, right: str, width: int) -> str:
    inner = max(5, width - 3)
    left_width = inner // 2
    right_width = inner - left_width
    return "|" + left[:left_width].ljust(left_width) + "|" + right[:right_width].ljust(right_width) + "|"


def _boxed_rule(width: int) -> str:
    inner = max(1, width - 2)
    return "+" + ("-" * inner) + "+"


def _build_arasaka_configuration_dummy_lines(
    *,
    width: int,
    patch: str,
    unicode: bool,
    snapshot: ExtendedBootTelemetry,
) -> list[str]:
    theme_key = "arasaka"
    lines = _logo_prefix(theme_key, width)
    lines.extend(
        [
            _boxed_rule(width),
            _boxed_full("ARASAKA SYSTEM CONFIGURATION / EXECUTIVE SECURITY GRID", width),
            _boxed_full(f"BUILD: v{SYSTEM_VERSION}  |  LAST PATCH {patch}", width),
            _boxed_full(AUTHOR_LINE, width),
            _boxed_rule(width),
            _boxed_full(f"MEMORY CHECK: {snapshot.total_memory_mb:,} MB  OK", width),
            _boxed_pair(
                f"Main Processor : {snapshot.physical_cores} PHYSICAL CORES",
                f"Thread Matrix  : {snapshot.logical_threads} LOGICAL THREADS",
                width,
            ),
            _boxed_pair(
                f"Base Memory    : {snapshot.total_memory_mb:,} MB",
                f"Memory Class   : {snapshot.total_memory_mb / 1024:.1f} GiB USABLE",
                width,
            ),
            _boxed_pair(
                f"AVAILABLE RAM  : {snapshot.available_memory_mb:,} MB",
                f"System Drive   : {snapshot.system_drive_free_gib:.1f}/{snapshot.system_drive_total_gib:.1f} GiB FREE",
                width,
            ),
            _boxed_pair(f"CPU Identity   : {snapshot.cpu_model}", f"Display Adapter: {snapshot.gpu_model}", width),
            _boxed_pair(f"Runtime        : {snapshot.os_version}", "Telemetry      : LIVE / PRIVATE", width),
            _boxed_pair("Display Type   : CORPORATE RED/BLACK", "Console Driver : VT-09 / UTF-8", width),
            _boxed_pair("Security ROM   : ARSK-7851", "Executive Port : ENCRYPTED", width),
            _boxed_rule(width),
            _boxed_full("MEMORY BANK / SECURE ENCLAVE INVENTORY", width),
            _boxed_pair("BANK 0         : CONSENSUS KERNEL", "ENCLAVE 0      : BLACKWALL ROOT", width),
            _boxed_pair("BANK 1         : FORECAST CACHE", "ENCLAVE 1      : EXECUTIVE KEYS", width),
            _boxed_pair("BANK 2         : TACTICAL MATRIX", "ENCLAVE 2      : AUDIT LEDGER", width),
            _boxed_pair("BANK 3         : QUORUM RESERVE", "ENCLAVE 3      : RECOVERY SEAL", width),
            _boxed_rule(width),
            _boxed_full("CORPORATE NETWORK ROUTING / TRUST DOMAINS", width),
            _boxed_pair("ROUTE 00       : ARASAKA_CORE", "TRUST          : INTERNAL", width),
            _boxed_pair("ROUTE 01       : EXEC_TRIBUNAL", "TRUST          : RESTRICTED", width),
            _boxed_pair("ROUTE 02       : CONSENSUS_BUS", "TRUST          : VERIFIED", width),
            _boxed_pair("ROUTE 03       : WAR_ROOM", "TRUST          : AUTHORIZED", width),
            _boxed_rule(width),
            _boxed_pair("BLACKWALL GATE : SECURED", "COUNTERINTEL   : ONLINE", width),
            _boxed_pair("RATIONALIS     : COMPLIANT", "AETERNUM       : YIELD VERIFIED", width),
            _boxed_pair("BELLATOR       : ARMED", "ARBITER        : AUTHORIZED", width),
            _boxed_rule(width),
            "",
            SUMMARY_LINES[theme_key],
            "CORPORATE ASSET AUDIT COMPLETE.",
            "EXECUTIVE CREDENTIAL ACCEPTED.",
            *_common_footer(theme_key, unicode),
        ]
    )
    return lines


def _build_helldivers_basic_dummy_lines(
    *,
    width: int,
    patch: str,
    unicode: bool,
    snapshot: ExtendedBootTelemetry,
) -> list[str]:
    theme_key = "helldivers"
    banner = f"*****  SUPER EARTH COMMAND BASIC v{SYSTEM_VERSION}  *****"
    lines = _logo_prefix(theme_key, width)
    lines.extend(
        [
            banner.center(width),
            "",
            f"{snapshot.total_memory_mb:,} MB RAM SYSTEM   {snapshot.total_memory_mb * 1024:,} DEMOCRATIC BYTES FREE",
            f"{snapshot.available_memory_mb:,} MB AVAILABLE TO DEFEND FREEDOM",
            f"{snapshot.physical_cores} PHYSICAL FREEDOM CORES / {snapshot.logical_threads} LOGICAL LIBERTY THREADS",
            f"PROCESSOR: {snapshot.cpu_model}",
            f"DISPLAY: {snapshot.gpu_model}",
            f"SYSTEM DISK: {snapshot.system_drive_free_gib:.1f}/{snapshot.system_drive_total_gib:.1f} GiB FREE",
            f"RUNTIME: {snapshot.os_version}",
            f"MINISTRY BUILD: v{SYSTEM_VERSION}   PATCH {patch}",
            AUTHOR_LINE,
            "",
            "READY.",
            'LOAD "MANAGED DEMOCRACY",8,1',
            "SEARCHING FOR MANAGED DEMOCRACY",
            "",
            'LOAD "$",8',
            '0 "SUPER EARTH DOS" 2A',
            '  64  "LIBERTY.KERN"       PRG',
            '  96  "STRATAGEM.BUS"      PRG',
            ' 128  "HELLDIVER.MATRIX"   PRG',
            ' 192  "TRIBUNAL.SYS"       PRG',
            ' 256  "CONSENSUS.WAR"      PRG',
            "65535 DEMOCRATIC BLOCKS FREE.",
            "READY.",
            "",
            "LIST",
            "10 PRINT \"INITIALIZING MINISTRY UPLINK\"",
            "20 VERIFY \"LIBERTY.KERN\",8,1",
            "30 POKE STRATAGEM_BUS,AUTHORIZED",
            "40 GOSUB HELLDIVER_DEPLOYMENT_MATRIX",
            "50 IF DISSENT>0 THEN GOTO 10",
            "60 SYS CONSENSUS_WAR_ROOM",
            "READY.",
            "",
            "LOADING STRATAGEM COMMAND BUS",
            "LOADING HELLDIVER DEPLOYMENT MATRIX",
            "LOADING SUPER EARTH TRIBUNAL",
            "VERIFYING CITIZEN AUTHORIZATION",
            "DISTRIBUTING APPROVED STRATAGEMS",
            "READY.",
            "RUN",
            SUMMARY_LINES[theme_key],
            *_common_footer(theme_key, unicode),
        ]
    )
    return lines


def _dual_column(left: str, right: str, width: int) -> str:
    inner = max(10, width - 4)
    left_width = inner // 2
    right_width = inner - left_width
    return left[:left_width].ljust(left_width) + " || " + right[:right_width].ljust(right_width)


def _build_janus_mirror_dummy_lines(
    *,
    width: int,
    patch: str,
    unicode: bool,
    snapshot: ExtendedBootTelemetry,
) -> list[str]:
    theme_key = "janus"
    checksum = f"{(snapshot.total_memory_mb * snapshot.logical_threads) & 0xFFFFFFFF:08X}"
    lines = _logo_prefix(theme_key, width)
    lines.extend(
        [
            _rule("JANUS DUAL-FRONT INITIALIZATION", width),
            f"BUILD: v{SYSTEM_VERSION}   LAST PATCH: {patch}   MIRROR MODE: ACTIVE",
            AUTHOR_LINE,
            "",
            _dual_column("PRIMARY FACE / FORWARD", "COUNTERPART FACE / REFLECTION", width),
            _dual_column("----------------------", "-----------------------------", width),
            _dual_column(
                f"PHYSICAL CORES : {snapshot.physical_cores}",
                f"LOGICAL THREADS: {snapshot.logical_threads}",
                width,
            ),
            _dual_column(
                f"MEMORY IMAGE   : {snapshot.total_memory_mb:,} MB",
                f"MIRROR RESERVE : {snapshot.total_memory_mb:,} MB",
                width,
            ),
            _dual_column(
                f"AVAILABLE RAM  : {snapshot.available_memory_mb:,} MB",
                f"SYSTEM DRIVE   : {snapshot.system_drive_free_gib:.1f} GiB FREE",
                width,
            ),
            _dual_column(f"CPU IDENTITY  : {snapshot.cpu_model}", f"GPU IDENTITY  : {snapshot.gpu_model}", width),
            _dual_column(f"HOST RUNTIME  : {snapshot.os_version}", "REFLECTION     : PRIVACY SAFE", width),
            _dual_column("RATIONALIS    : ONLINE", "COUNTERLOGIC   : ONLINE", width),
            _dual_column("AETERNUM      : ONLINE", "COUNTERFUTURE  : ONLINE", width),
            _dual_column("BELLATOR      : ONLINE", "COUNTERFORCE   : ONLINE", width),
            _dual_column(f"CHECKSUM      : {checksum}", f"CHECKSUM      : {checksum}", width),
            "",
            _rule("MIRROR RECONCILIATION LEDGER", width),
            _dual_column("PHASE 01 / MEMORY MAP", "REFLECTION 01 / MEMORY MAP", width),
            _dual_column("PHASE 02 / LOGIC STATE", "REFLECTION 02 / LOGIC STATE", width),
            _dual_column("PHASE 03 / FORECAST", "REFLECTION 03 / FORECAST", width),
            _dual_column("PHASE 04 / TACTICAL", "REFLECTION 04 / TACTICAL", width),
            _dual_column("PHASE 05 / QUORUM", "REFLECTION 05 / QUORUM", width),
            _dual_column("VECTOR A      : ALIGNED", "VECTOR B      : ALIGNED", width),
            _dual_column("CLOCK DRIFT   : +0.000", "CLOCK DRIFT   : -0.000", width),
            _dual_column("IDENTITY HASH : VERIFIED", "IDENTITY HASH : VERIFIED", width),
            _dual_column("HANDSHAKE     : ACCEPTED", "HANDSHAKE     : ACCEPTED", width),
            "",
            _rule("DUAL-CHANNEL QUORUM", width),
            _dual_column("RATIONALIS VOTE: AFFIRM", "COUNTERLOGIC   : AFFIRM", width),
            _dual_column("AETERNUM VOTE  : AFFIRM", "COUNTERFUTURE  : AFFIRM", width),
            _dual_column("BELLATOR VOTE  : AFFIRM", "COUNTERFORCE   : AFFIRM", width),
            _dual_column("ARBITER SEAL   : LOCKED", "MIRROR SEAL    : LOCKED", width),
            _dual_column("INPUT CHANNEL  : OPEN", "OUTPUT CHANNEL : OPEN", width),
            _dual_column("PRIMARY NONCE  : 7A15", "REFLECTED NONCE: 51A7", width),
            _dual_column("EVENT ORDER    : FORWARD", "EVENT ORDER    : REVERSE", width),
            _dual_column("DECISION STATE : CONSENT", "DECISION STATE : CONSENT", width),
            _dual_column("QUORUM RESULT  : COMPLETE", "QUORUM RESULT  : COMPLETE", width),
            "",
            "< PRIMARY AND COUNTERPART CHECKSUMS AGREE >".center(width),
            "< DUAL-CHANNEL IDENTITY LOCKED >".center(width),
            SUMMARY_LINES[theme_key],
            *_common_footer(theme_key, unicode),
        ]
    )
    return lines


def _ritual_frame(text: str, width: int, unicode: bool) -> str:
    left, right = ("║", "║") if unicode else ("|", "|")
    inner = max(1, width - 2)
    return left + (" " + text)[:inner].ljust(inner) + right


def _ritual_rule(width: int, unicode: bool) -> str:
    if unicode:
        return "╠" + ("═" * max(1, width - 2)) + "╣"
    return "+" + ("=" * max(1, width - 2)) + "+"


def _build_wh40k_ritual_dummy_lines(
    *,
    width: int,
    patch: str,
    unicode: bool,
    snapshot: ExtendedBootTelemetry,
) -> list[str]:
    theme_key = "wh40k"
    top = ("╔" + "═" * max(1, width - 2) + "╗") if unicode else _ritual_rule(width, False)
    bottom = ("╚" + "═" * max(1, width - 2) + "╝") if unicode else _ritual_rule(width, False)
    lines = _logo_prefix(theme_key, width)
    lines.extend(
        [
            top,
            _ritual_frame("LITANY OF AWAKENING / SANCTIFIED COGITATOR RITE", width, unicode),
            _ritual_frame(f"COGITATOR BUILD: v{SYSTEM_VERSION} / PATCH REF {patch}", width, unicode),
            _ritual_frame(AUTHOR_LINE, width, unicode),
            _ritual_rule(width, unicode),
            _ritual_frame("By seal of the Omnissiah, let dormant circuits know purpose.", width, unicode),
            _ritual_frame(
                f"MEMORY RELIQUARY ........ {snapshot.total_memory_mb:,} MB ........ SANCTIFIED",
                width,
                unicode,
            ),
            _ritual_frame(
                f"AVAILABLE MEMORY ........ {snapshot.available_memory_mb:,} MB ....... CONSECRATED",
                width,
                unicode,
            ),
            _ritual_frame(
                f"PROCESSOR CHOIR ......... {snapshot.physical_cores} CORES / {snapshot.logical_threads} THREADS .... HARMONIZED",
                width,
                unicode,
            ),
            _ritual_frame(f"PROCESSOR RELIC ......... {snapshot.cpu_model}", width, unicode),
            _ritual_frame(f"DISPLAY RELIC ........... {snapshot.gpu_model}", width, unicode),
            _ritual_frame(
                f"SYSTEM VAULT ............ {snapshot.system_drive_free_gib:.1f}/{snapshot.system_drive_total_gib:.1f} GiB FREE",
                width,
                unicode,
            ),
            _ritual_frame(f"HOST CHRONICLE .......... {snapshot.os_version}", width, unicode),
            _ritual_frame("RATIONALIS LOGIS SHRINE ........................ BLESSED", width, unicode),
            _ritual_frame("AETERNUM CHRONICLE VAULT ....................... BLESSED", width, unicode),
            _ritual_frame("BELLATOR MUNITORUM CORE ........................ ARMED", width, unicode),
            _ritual_frame("ARBITER SANCTION SEAL .......................... ACCEPTED", width, unicode),
            _ritual_rule(width, unicode),
            _ritual_frame("FIRST CANTICLE: PURGE THE CACHE OF DOUBT.", width, unicode),
            _ritual_frame("  HEXAGRAMMATIC MEMORY WARDS ................... INSCRIBED", width, unicode),
            _ritual_frame("  NOOSPHERIC ROUTING SIGILS .................... ALIGNED", width, unicode),
            _ritual_frame("SECOND CANTICLE: GIVE VOICE TO THE PROCESSOR CHOIR.", width, unicode),
            _ritual_frame("  LOGIS CYCLES ................................. NOMINAL", width, unicode),
            _ritual_frame("  CHRONICLE CLOCK .............................. TRUE", width, unicode),
            _ritual_frame("THIRD CANTICLE: BIND THE QUORUM TO ITS SACRED TASK.", width, unicode),
            _ritual_frame("  TRIPLE-MIND CONSENSUS ........................ UNANIMOUS", width, unicode),
            _ritual_frame("  HUMAN INTERLOCK .............................. SEALED", width, unicode),
            _ritual_frame("  WAR-ROOM DATA THRONE ......................... AWAITING", width, unicode),
            _ritual_rule(width, unicode),
            _ritual_frame("THE MACHINE SPIRIT STIRS.  THE NOOSPHERE ANSWERS.", width, unicode),
            _ritual_frame(SUMMARY_LINES[theme_key], width, unicode),
            bottom,
            *_common_footer(theme_key, unicode),
        ]
    )
    return lines


def build_theme_dummy_lines(
    theme_id: str,
    *,
    width: int = DEFAULT_WIDTH,
    patch_date: str | None = None,
    unicode: bool = True,
    layout: str = "full",
    telemetry: ExtendedBootTelemetry | None = None,
    provider_status: dict[str, object] | None = None,
) -> list[str]:
    theme_key = resolve_theme_key(theme_id)
    if theme_key not in SUPPORTED_THEME_KEYS:
        raise ValueError(f"Unsupported prototype theme: {theme_id}")
    active_width = _terminal_width(width)
    patch = patch_date or _default_patch_date()
    snapshot = telemetry or capture_extended_boot_telemetry()
    builders = {
        "eva": _build_eva_dense_dummy_lines,
        "military": _build_military_post_dummy_lines,
        "arasaka": _build_arasaka_configuration_dummy_lines,
        "helldivers": _build_helldivers_basic_dummy_lines,
        "janus": _build_janus_mirror_dummy_lines,
        "wh40k": _build_wh40k_ritual_dummy_lines,
    }
    lines = builders[theme_key](width=active_width, patch=patch, unicode=unicode, snapshot=snapshot)
    if provider_status is not None:
        loading_label = get_loading_style(theme_key).label
        loading_index = lines.index(loading_label)
        lines[loading_index:loading_index] = [
            *_themed_provider_lines(theme_key, provider_status, active_width, unicode),
            "",
        ]
    compact = layout == "compact" or (layout == "auto" and active_width < COMPACT_WIDTH)
    if compact:
        lines = _compact_preview_lines(theme_key, lines, active_width, unicode)
    return _fit_preview_lines(lines, active_width)


def build_eva_dummy_lines(
    *,
    width: int = DEFAULT_WIDTH,
    patch_date: str | None = None,
    unicode: bool = True,
    layout: str = "full",
) -> list[str]:
    return build_theme_dummy_lines(
        "eva",
        width=width,
        patch_date=patch_date,
        unicode=unicode,
        layout=layout,
    )


def _stdout_supports(text: str) -> bool:
    encoding = sys.stdout.encoding or "utf-8"
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def _configure_stdout() -> None:
    """Keep Windows pipes and legacy consoles from rejecting the prototype glyphs."""
    if os.name != "nt" or not hasattr(sys.stdout, "reconfigure"):
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def _ansi_color(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return f"\x1b[38;2;{red};{green};{blue}m"


def _ansi_background(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return f"\x1b[48;2;{red};{green};{blue}m"


def _palette(enabled: bool, theme_id: str = "eva") -> EvaPalette:
    if not enabled:
        return EvaPalette(theme_key=resolve_theme_key(theme_id))
    try:
        from colorama import just_fix_windows_console

        just_fix_windows_console()
    except Exception:
        pass
    theme_key = resolve_theme_key(theme_id)
    colors = _boot_color_values(theme_key)
    return EvaPalette(
        orange=_ansi_color(colors["primary"]),
        red=_ansi_color(colors["data"]),
        cyan=_ansi_color(colors["success"]),
        white=_ansi_color(colors["text"]),
        warning=_ansi_color(colors["warning"]),
        reset="\x1b[0m",
        logo=_ansi_color(colors["logo"]),
        background=_ansi_background("#2636b8") if theme_key == "helldivers" else "",
        theme_key=theme_key,
    )


def _clear(enabled: bool) -> None:
    if enabled:
        os.system("cls" if os.name == "nt" else "clear")


def _extended_diagnostics_lines(
    theme_key: str,
    telemetry: ExtendedBootTelemetry,
    width: int,
) -> list[str]:
    rows = [
        f"CPU MODEL       : {telemetry.cpu_model}",
        f"CPU TOPOLOGY    : {telemetry.physical_cores} PHYSICAL / {telemetry.logical_threads} LOGICAL",
        f"MEMORY          : {telemetry.available_memory_mb:,} MB AVAILABLE / {telemetry.total_memory_mb:,} MB TOTAL",
        f"DISPLAY ADAPTER : {telemetry.gpu_model}",
        f"SYSTEM DRIVE    : {telemetry.system_drive_free_gib:.1f} GiB FREE / {telemetry.system_drive_total_gib:.1f} GiB TOTAL",
        f"OS RUNTIME      : {telemetry.os_version}",
        "PRIVACY         : USER, NETWORK AND SERIAL IDENTIFIERS SUPPRESSED",
    ]
    return [_rule(f"{THEMES[theme_key].display_name.upper()} EXTENDED DIAGNOSTICS", width), *rows, ""]


def _styled_segments(line: str, palette: EvaPalette) -> list[tuple[str, str]]:
    if not palette.reset:
        return [("", line)]
    stripped = line.strip()
    if not stripped:
        return [(palette.white, line)]
    if palette.theme_key == "wh40k":
        if stripped.startswith(("╔", "╚", "╠", "+")):
            return [(palette.orange, line)]
        if stripped.startswith(("║", "|")) and stripped.endswith(("║", "|")) and len(line) >= 2:
            left_at = line.find(stripped[0])
            right_at = line.rfind(stripped[-1])
            return [
                (palette.white, line[:left_at]),
                (palette.orange, line[left_at : left_at + 1]),
                (palette.white, line[left_at + 1 : right_at]),
                (palette.orange, line[right_at : right_at + 1]),
                (palette.white, line[right_at + 1 :]),
            ]
    if palette.theme_key == "arasaka" and stripped.startswith(("|", "+")):
        if stripped.startswith("+"):
            return [(palette.orange, line)]
        segments: list[tuple[str, str]] = []
        cursor = 0
        for match in re.finditer(r"\|", line):
            segments.append((palette.white, line[cursor : match.start()]))
            segments.append((palette.orange, "|"))
            cursor = match.end()
        segments.append((palette.white, line[cursor:]))
        return segments
    if palette.theme_key == "janus" and " || " in line:
        left, right = line.split(" || ", 1)
        return [(palette.orange, left), (palette.white, " || "), (palette.cyan, right)]
    if "UNAVAILABLE" in stripped or "FALLBACK" in stripped:
        return [(palette.warning, line)]
    if (
        "BIOS v" in stripped
        or "COMMAND BASIC" in stripped
        or "LITANY OF AWAKENING" in stripped
        or "JANUS DUAL-FRONT" in stripped
        or stripped.startswith(("-", "+", "╔", "╚", "╠"))
    ):
        return [(palette.orange, line)]
    if ("[" in stripped and "]" in stripped and "%" in stripped) or stripped.startswith(
        ("INITIALIZING", "LOAD ", "RUN")
    ):
        return [(palette.orange, line)]
    if stripped.endswith((" READY", " AWAKENED")) or stripped == "READY." or stripped in HANDOFF_LINES.values():
        return [(palette.cyan, line)]
    if stripped.startswith(("Copyright", "MAGI Consensus Array", "DATE", "SERIAL:", "Chief Architect:", "Janus ", "LAST PATCH:")):
        return [(palette.white, line)]
    for status in (
        "AUTHORIZED",
        "SANCTIFIED",
        "HARMONIZED",
        "COMPLIANT",
        "SECURED",
        "ACCEPTED",
        "COMPLETE.",
        "BLESSED",
        "VERIFIED",
        "ENABLED",
        "ALIGNED",
        "AFFIRM",
        "COMPLETE",
        "LOCKED",
        "LINKED",
        "ONLINE",
        "ARMED",
        "OK",
    ):
        if stripped.endswith(status):
            split_at = line.rfind(status)
            return [(palette.red, line[:split_at]), (palette.cyan, line[split_at:])]
    if stripped.startswith(("DEVICE", "ADDR", "NODE")):
        return [(palette.white, line)]
    if palette.theme_key in {"military", "helldivers", "wh40k"}:
        return [(palette.white, line)]
    return [(palette.red, line)]


def _write_styled_line(line: str, palette: EvaPalette, width: int | None = None) -> None:
    display_line = line.ljust(width) if palette.background and width else line
    if palette.background:
        sys.stdout.write(palette.background)
    for color, text in _styled_segments(display_line, palette):
        if color:
            sys.stdout.write(color)
        sys.stdout.write(text)
    if palette.reset:
        sys.stdout.write(palette.reset)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _write_styled_inline(line: str, palette: EvaPalette) -> None:
    for color, text in _styled_segments(line, palette):
        if color:
            sys.stdout.write(color)
        sys.stdout.write(text)
    if palette.reset:
        sys.stdout.write(palette.reset)


def _poll_controls(controls: PreviewControls | None) -> None:
    if controls is None or os.name != "nt":
        return
    try:
        import msvcrt

        while msvcrt.kbhit():
            key = msvcrt.getwch()
            if key in {"\x00", "\xe0"}:
                code = ord(msvcrt.getwch())
                if code == 60:  # F2
                    controls.extended = True
                elif code == 134:  # F12
                    controls.static = True
                continue
            if key in {"\x1b", " "}:
                controls.skip = True
    except (ImportError, OSError):
        return


def _wait_with_controls(duration: float, controls: PreviewControls | None) -> bool:
    deadline = time.monotonic() + max(0.0, duration)
    while time.monotonic() < deadline:
        _poll_controls(controls)
        if controls and (controls.skip or controls.static):
            return False
        time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))
    return True


def _choreography_multiplier(theme_key: str, line: str) -> float:
    stripped = line.strip()
    if theme_key == "military":
        return 0.35
    if theme_key == "arasaka":
        return 1.45 if stripped.startswith("+") else 0.70
    if theme_key == "helldivers":
        return 1.70 if stripped.startswith(("LOAD ", "LIST", "RUN", "READY.")) else 0.85
    if theme_key == "janus":
        return 0.75
    if theme_key == "wh40k":
        return 0.25 if stripped.startswith(("╔", "╚", "╠", "+")) else 1.35
    return 1.0


def _balanced_timing(
    speed: str,
    theme_key: str,
    logo_lines: Sequence[str],
    animated_lines: Sequence[str],
    compact: bool,
) -> tuple[float, float, float, float, float]:
    """Allocate a comparable duration while preserving each theme's cadence."""
    target = TARGET_BOOT_SECONDS[speed] * (0.76 if compact else 1.0)
    char_units = 0
    line_units = 0.0
    for line in animated_lines:
        if "MEMORY CHECK:" in line:
            continue
        if theme_key == "janus" and " || " in line:
            left, right = line.split(" || ", 1)
            char_units += max(len(left.rstrip()), len(right.rstrip()))
        else:
            char_units += len(line)
        line_units += _choreography_multiplier(theme_key, line)
        if theme_key == "helldivers" and line.strip() == "READY.":
            line_units += 8.0

    logo_hold = target * 0.05
    logo_line_delay = target * 0.08 / max(1, len(logo_lines))
    loading_step_delay = target * 0.08 / 26
    memory_budget = 0.43 if any("MEMORY CHECK:" in line for line in animated_lines) else 0.0
    remaining = max(1.0, target - logo_hold - (logo_line_delay * len(logo_lines)) - (loading_step_delay * 26) - memory_budget)
    char_delay = max(0.00065, remaining * 0.78 / max(1, char_units))
    line_delay = max(0.003, remaining * 0.22 / max(1.0, line_units))
    return char_delay, line_delay, logo_line_delay, logo_hold, loading_step_delay


def _type_janus_mirror_line(
    line: str,
    char_delay: float,
    line_delay: float,
    palette: EvaPalette,
    controls: PreviewControls | None,
) -> bool:
    left, right = line.split(" || ", 1)
    steps = max(len(left.rstrip()), len(right.rstrip()))
    burst = max(1, round(MIN_RENDER_SLEEP / max(char_delay, 0.0001)))
    for position in range(0, steps + burst, burst):
        _poll_controls(controls)
        if controls and (controls.skip or controls.static):
            return False
        left_frame = left[:position].ljust(len(left))
        right_frame = right[:position]
        sys.stdout.write(
            f"\r{palette.orange}{left_frame}{palette.white} || {palette.cyan}{right_frame}{palette.reset}"
        )
        sys.stdout.flush()
        if not _wait_with_controls(max(MIN_RENDER_SLEEP, char_delay * burst), controls):
            return False
    sys.stdout.write("\n")
    sys.stdout.flush()
    return _wait_with_controls(line_delay * _choreography_multiplier("janus", line), controls)


def _type_styled_line(
    line: str,
    char_delay: float,
    line_delay: float,
    palette: EvaPalette,
    width: int | None = None,
    controls: PreviewControls | None = None,
) -> bool:
    if palette.theme_key == "janus" and " || " in line:
        return _type_janus_mirror_line(line, char_delay, line_delay, palette, controls)
    if not line:
        if palette.background and width:
            sys.stdout.write(f"{palette.background}{' ' * width}{palette.reset}\n")
            sys.stdout.flush()
        else:
            print()
        return _wait_with_controls(line_delay, controls)
    if palette.background:
        sys.stdout.write(palette.background)
    for color, text in _styled_segments(line, palette):
        if color:
            sys.stdout.write(color)
        burst_size = max(1, round(MIN_RENDER_SLEEP / char_delay))
        for offset in range(0, len(text), burst_size):
            _poll_controls(controls)
            if controls and (controls.skip or controls.static):
                return False
            burst = text[offset : offset + burst_size]
            sys.stdout.write(burst)
            sys.stdout.flush()
            if not _wait_with_controls(max(MIN_RENDER_SLEEP, char_delay * len(burst)), controls):
                return False
    if palette.background and width and len(line) < width:
        sys.stdout.write(" " * (width - len(line)))
    if palette.reset:
        sys.stdout.write(palette.reset)
    sys.stdout.write("\n")
    sys.stdout.flush()
    if palette.theme_key == "helldivers" and line.strip() == "READY.":
        for _ in range(2):
            sys.stdout.write(f"{palette.white}█{palette.reset}")
            sys.stdout.flush()
            if not _wait_with_controls(line_delay * 2.5, controls):
                return False
            sys.stdout.write("\b \b")
            sys.stdout.flush()
            if not _wait_with_controls(line_delay * 1.5, controls):
                return False
    return _wait_with_controls(
        line_delay * _choreography_multiplier(palette.theme_key, line),
        controls,
    )


def _print_lines(
    lines: Iterable[str],
    delay: float,
    color: str,
    reset: str,
    background: str = "",
    width: int | None = None,
    controls: PreviewControls | None = None,
) -> bool:
    for line in lines:
        display_line = line.ljust(width) if background and width else line
        if color or background:
            print(f"{background}{color}{display_line}{reset}")
        else:
            print(display_line)
        if delay and not _wait_with_controls(delay, controls):
            return False
    return True


def _print_styled_lines(lines: Iterable[str], palette: EvaPalette, width: int | None = None) -> None:
    for line in lines:
        _write_styled_line(line, palette, width)


def _type_styled_lines(
    lines: Iterable[str],
    char_delay: float,
    line_delay: float,
    palette: EvaPalette,
    width: int | None = None,
    controls: PreviewControls | None = None,
    memory_total_mb: int | None = None,
) -> bool:
    for line in lines:
        if memory_total_mb is not None and "MEMORY CHECK:" in line:
            if not _animate_memory_count(memory_total_mb, palette, controls, width or DEFAULT_WIDTH):
                return False
            continue
        if not _type_styled_line(line, char_delay, line_delay, palette, width, controls):
            return False
    return True


def _animate_memory_count(
    total_memory_mb: int,
    palette: EvaPalette,
    controls: PreviewControls | None,
    width: int,
) -> bool:
    steps = 16
    for step in range(steps + 1):
        current = round(total_memory_mb * step / steps)
        status = "  OK" if step == steps else ""
        content = f"MEMORY CHECK: {current:>10,} MB{status}"
        line = _boxed_full(content, width) if palette.theme_key == "arasaka" else content
        sys.stdout.write("\r")
        _write_styled_inline(line, palette)
        sys.stdout.flush()
        if not _wait_with_controls(0.025, controls):
            return False
    sys.stdout.write("\n")
    return True


def render_theme_dummy(
    theme_id: str,
    *,
    speed: str = "normal",
    patch_date: str | None = None,
    width: int | None = None,
    clear: bool = True,
    color: bool = True,
    layout: str = "auto",
    reduced_motion: bool = False,
    interactive: bool = True,
    provider_status: dict[str, object] | None = None,
) -> None:
    _configure_stdout()
    theme_key = resolve_theme_key(theme_id)
    active_width = _terminal_width(width)
    palette = _palette(color, theme_key)
    unicode = _stdout_supports("■□")
    telemetry = capture_extended_boot_telemetry()
    static_lines = build_theme_dummy_lines(
        theme_key,
        width=active_width,
        patch_date=patch_date,
        unicode=unicode,
        layout=layout,
        telemetry=telemetry,
        provider_status=provider_status,
    )
    logo_prefix = _logo_prefix(theme_key, active_width)
    logo_lines = logo_prefix[:-1]
    loading_label = get_loading_style(theme_key).label
    controls = PreviewControls() if interactive else None
    body_start = len(logo_lines) + 1
    body = static_lines[body_start:]
    loading_index = body.index(loading_label)
    animated_lines = [*body[: loading_index + 1], *body[loading_index + 2 :]]
    compact = layout == "compact" or (layout == "auto" and active_width < COMPACT_WIDTH)
    char_delay, line_delay, logo_line_delay, logo_hold, loading_step_delay = _balanced_timing(
        speed,
        theme_key,
        logo_lines,
        animated_lines,
        compact,
    )

    def finish_immediately() -> None:
        _clear(clear)
        _print_styled_lines(static_lines, palette, active_width)
        if controls and controls.extended:
            _print_styled_lines(
                _extended_diagnostics_lines(theme_key, telemetry, active_width),
                palette,
                active_width,
            )

    if reduced_motion:
        finish_immediately()
        return

    _clear(clear)
    logo_complete = _print_lines(
        logo_lines,
        logo_line_delay,
        palette.logo,
        palette.reset,
        palette.background,
        active_width,
        controls,
    )
    if not logo_complete or not _wait_with_controls(logo_hold, controls):
        finish_immediately()
        return
    _clear(clear)

    if not _type_styled_lines(
        body[: loading_index + 1],
        char_delay,
        line_delay,
        palette,
        active_width,
        controls,
        telemetry.total_memory_mb if theme_key in {"military", "arasaka"} else None,
    ):
        finish_immediately()
        return

    extended_rendered = False
    if controls and controls.extended:
        if not _type_styled_lines(
            _extended_diagnostics_lines(theme_key, telemetry, active_width),
            char_delay * 0.6,
            line_delay,
            palette,
            active_width,
            controls,
        ):
            finish_immediately()
            return
        extended_rendered = True

    for percent in range(0, 101, 4):
        _poll_controls(controls)
        if controls and (controls.skip or controls.static):
            finish_immediately()
            return
        bar = format_theme_loading_bar(theme_key, percent, unicode=unicode)
        display_bar = bar.ljust(active_width) if palette.background else bar
        if palette.orange or palette.background:
            sys.stdout.write(f"\r{palette.background}{palette.orange}{display_bar}{palette.reset}")
        else:
            sys.stdout.write(f"\r{bar}")
        sys.stdout.flush()
        if not _wait_with_controls(loading_step_delay, controls):
            finish_immediately()
            return
    print()
    if controls and controls.extended and not extended_rendered:
        if not _type_styled_lines(
            _extended_diagnostics_lines(theme_key, telemetry, active_width),
            char_delay * 0.6,
            line_delay,
            palette,
            active_width,
            controls,
        ):
            finish_immediately()
            return
    if not _type_styled_lines(
        body[loading_index + 2 :],
        char_delay,
        line_delay,
        palette,
        active_width,
        controls,
    ):
        finish_immediately()


def render_eva_dummy(
    *,
    speed: str = "normal",
    patch_date: str | None = None,
    width: int | None = None,
    clear: bool = True,
    color: bool = True,
) -> None:
    render_theme_dummy(
        "eva",
        speed=speed,
        patch_date=patch_date,
        width=width,
        clear=clear,
        color=color,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Isolated interchangeable themed boot-layout prototypes.")
    parser.add_argument(
        "--theme",
        choices=tuple(key.upper() for key in SUPPORTED_THEME_KEYS),
        default="EVA",
        type=str.upper,
        help="Theme preview to render (default: EVA).",
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Print the completed color frame immediately; omit this flag for the animated BIOS sequence.",
    )
    parser.add_argument("--speed", choices=tuple(SPEEDS), default="normal")
    parser.add_argument(
        "--layout",
        choices=("auto", "full", "compact"),
        default="auto",
        help="Responsive layout mode; auto uses compact mode below 96 columns.",
    )
    parser.add_argument("--patch-date", default=None, help="Override LAST PATCH (YYYY-MM-DD).")
    parser.add_argument("--width", type=int, default=None, help="Preview width; minimum 64 columns.")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear the terminal between stages.")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal theme colors.")
    parser.add_argument(
        "--reduced-motion",
        action="store_true",
        help="Render the complete themed screen immediately without animation.",
    )
    parser.add_argument(
        "--no-controls",
        action="store_true",
        help="Disable ESC/Space skip, F2 extended diagnostics and F12 static-view controls.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdout()
    args = _parser().parse_args(argv)
    theme_key = resolve_theme_key(args.theme)
    width = _terminal_width(args.width)
    unicode = _stdout_supports("■□")
    if args.static:
        telemetry = capture_extended_boot_telemetry()
        palette = _palette(not args.no_color, theme_key)
        _print_styled_lines(
            build_theme_dummy_lines(
                theme_key,
                width=width,
                patch_date=args.patch_date,
                unicode=unicode,
                layout=args.layout,
                telemetry=telemetry,
            ),
            palette,
            width,
        )
        return 0
    render_theme_dummy(
        theme_key,
        speed=args.speed,
        patch_date=args.patch_date,
        width=width,
        clear=not args.no_clear,
        color=not args.no_color,
        layout=args.layout,
        reduced_motion=args.reduced_motion,
        interactive=not args.no_controls,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
