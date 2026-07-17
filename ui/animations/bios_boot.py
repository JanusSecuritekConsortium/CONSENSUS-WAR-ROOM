from __future__ import annotations

import os
import random
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List

from config.version import SYSTEM_AUTHOR, SYSTEM_LAST_PATCH_DATE, SYSTEM_ORGANIZATION, SYSTEM_VERSION
from core.paths import RESOURCE_ROOT
from ui.boot.phrases import node_boot_lines
from ui.boot.registry import select_detected_devices, select_post_checks
from ui.animations.loading import format_loading_bar, get_loading_style, render_loading_console
from ui.themes.catalog import THEMES, resolve_theme_key


LOGO_DIR = RESOURCE_ROOT / "static" / "logos"

SPEED_DELAYS = {
    "fast": 0.018,
    "normal": 0.05,
    "slow": 0.105,
}
RANDOM_DELAY_RANGE = (0.025, 0.075)

DEFAULT_BOOT_WIDTH = 100
TRIBUNAL_PHRASE_SEED = 0
MILITARY_BOOT_LOGO_MAX_WIDTH = 56
MILITARY_BOOT_LOGO_MAX_HEIGHT = 28
BOOT_LOGO_DENSITY_GLYPHS = " .:-=+*#%@"
MIN_RENDER_SLEEP = 0.016

DENSE_READY_LINES = {
    "military": "EXCOMM WAR ROOM READY",
    "eva": "MAGI CONSENSUS ARRAY READY",
    "nerv": "NERV MAGI INTERLOCK READY",
    "wh40k": "IMPERIAL COGITATOR AWAKENED",
    "helldivers": "MANAGED DEMOCRACY INTERFACE READY",
    "arasaka": "ARASAKA EXECUTIVE GRID READY",
    "janus": "JANUS MIRROR CHANNEL READY",
}

DENSE_SUMMARY_LINES = {
    "military": "THREATCON: GREEN    COMMAND INTEGRITY: 99.91%    AUTHORIZATION BUS: ARMED",
    "eva": "PATTERN ANALYSIS: BLUE    CONSENSUS INTEGRITY: 99.97%    HUMAN INTERLOCK: ARMED",
    "nerv": "PATTERN ANALYSIS: BLUE    MAGI INTERLOCK: 99.97%    CENTRAL DOGMA LINK: ARMED",
    "wh40k": "MACHINE SPIRIT: PURE    NOOSPHERIC INTEGRITY: 99.88%    SANCTION SEAL: BLESSED",
    "helldivers": "LIBERTY INDEX: MAXIMUM    DEMOCRACY INTEGRITY: 99.93%    STRATAGEM BUS: ARMED",
    "arasaka": "BLACKWALL: SECURED    CLEARANCE INTEGRITY: 99.94%    EXECUTIVE CHANNEL: ARMED",
    "janus": "MIRROR STATE: ALIGNED    DUAL-CHANNEL INTEGRITY: 99.95%    COUNTERPART GATE: ARMED",
}

DENSE_CONFIGURATION_ROWS = (
    ("0D0E0", "SYS", "1", "5296", "kernel"),
    ("0D22C", "SYS", "1", "2416", "terminal_driver"),
    ("0D2C4", "2081", "1", "16384", "consensus_bus"),
    ("0D6C5", "DBFE", "1", "21392", "<free>"),
    ("0DE02", "E000", "1", "8160", "<free>"),
    ("00586", "SYS", "1", "2144", "memory_alignment"),
    ("0060D", "SYS", "1", "3968", "forecast_vector"),
    ("00706", "SYS", "1", "3312", "judgement_gate"),
)


@dataclass(frozen=True)
class BootTerminalPalette:
    logo: str = ""
    primary: str = ""
    data: str = ""
    success: str = ""
    text: str = ""
    warning: str = ""
    reset: str = ""


def _terminal_width() -> int:
    return max(80, shutil.get_terminal_size((DEFAULT_BOOT_WIDTH, 24)).columns)


def _center(line: str, width: int | None = None) -> str:
    active_width = width or _terminal_width()
    if len(line) >= active_width:
        return line
    return (" " * ((active_width - len(line)) // 2)) + line


def _center_lines_block(lines: Iterable[str], width: int | None = None) -> List[str]:
    active_width = width or _terminal_width()
    material = list(lines)
    block_width = max((len(line.strip()) for line in material), default=0)
    pad = max(0, (active_width - block_width) // 2)
    return [(" " * pad) + line.strip() for line in material]


def _center_block(text: str, width: int | None = None) -> str:
    active_width = width or _terminal_width()
    lines = text.rstrip("\n").splitlines()
    block_width = max((len(line) for line in lines), default=0)
    pad = max(0, (active_width - block_width) // 2)
    return "\n".join((" " * pad) + line for line in lines)


def _legacy_center(line: str, width: int = DEFAULT_BOOT_WIDTH) -> str:
    return line.center(width) if line else line


def _system_memory_mb() -> tuple[int, bool]:
    try:
        import psutil  # type: ignore

        return max(1, round(psutil.virtual_memory().total / (1024**2))), False
    except Exception:
        pass
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return max(1, round(status.ullTotalPhys / (1024**2))), False
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return max(1, round((pages * page_size) / (1024**2))), False
    except Exception:
        return 65536, True


def _memory_steps_mb(total_memory_mb: int | None = None) -> tuple[List[int], bool]:
    detected, fallback = _system_memory_mb()
    total = max(1, total_memory_mb or detected)
    block = 8192 if total >= 8192 else max(1, total // 4)
    raw_steps = list(range(block, total + 1, block))
    if not raw_steps or raw_steps[-1] != total:
        raw_steps.append(total)
    steps: List[int] = []
    for step in raw_steps:
        if not steps or step != steps[-1]:
            steps.append(step)
    return steps, fallback and total_memory_mb is None


def _visible_date() -> str:
    return date.today().isoformat()


def _logo_text(name: str) -> str:
    return (LOGO_DIR / name).read_text(encoding="utf-8")


def _theme_logo_text(theme_id: str) -> str:
    theme_key = resolve_theme_key(theme_id)
    theme = THEMES.get(theme_key, THEMES["nerv"])
    return Path(theme.logo_path).read_text(encoding="utf-8")


def _fit_terminal_logo(text: str, max_width: int, max_height: int) -> str:
    lines = text.rstrip("\n").splitlines()
    source_height = len(lines)
    source_width = max((len(line) for line in lines), default=0)
    if not lines or source_width == 0:
        return ""
    if source_width <= max_width and source_height <= max_height:
        return "\n".join(lines)

    scale = min(max_width / source_width, max_height / source_height)
    target_width = max(1, round(source_width * scale))
    target_height = max(1, round(source_height * scale))
    grid = [line.ljust(source_width) for line in lines]
    result: List[str] = []
    for target_y in range(target_height):
        source_y0 = target_y * source_height // target_height
        source_y1 = max(source_y0 + 1, ((target_y + 1) * source_height + target_height - 1) // target_height)
        output_line: List[str] = []
        for target_x in range(target_width):
            source_x0 = target_x * source_width // target_width
            source_x1 = max(source_x0 + 1, ((target_x + 1) * source_width + target_width - 1) // target_width)
            sample_count = (source_y1 - source_y0) * (source_x1 - source_x0)
            filled = sum(
                grid[source_y][source_x] != " "
                for source_y in range(source_y0, source_y1)
                for source_x in range(source_x0, source_x1)
            )
            density = filled / sample_count
            glyph_index = round(density * (len(BOOT_LOGO_DENSITY_GLYPHS) - 1))
            if filled and glyph_index == 0:
                glyph_index = 1
            output_line.append(BOOT_LOGO_DENSITY_GLYPHS[glyph_index])
        result.append("".join(output_line).rstrip())
    return "\n".join(result)


def _theme_boot_logo_text(theme_id: str) -> str:
    logo = _theme_logo_text(theme_id)
    if resolve_theme_key(theme_id) == "military":
        return _fit_terminal_logo(
            logo,
            max_width=MILITARY_BOOT_LOGO_MAX_WIDTH,
            max_height=MILITARY_BOOT_LOGO_MAX_HEIGHT,
        )
    return logo.rstrip("\n")


def _bios_header_lines(theme_id: str, version: str) -> List[str]:
    theme_key = resolve_theme_key(theme_id)
    visible_date = _visible_date()
    if theme_key == "wh40k":
        return [
            f"IMPERIAL COGITATOR BIOS v{version}",
            "+++ ADEPTUS MECHANICUS COGITATOR RITE +++",
            "Adeptus Mechanicus Noospheric Terminal / Machine Spirit Litany",
            "DATE REF: 0918015.M03",
            "SERIAL: OMNISSIAH-COG-7851 | DATE REF: 0918015.M03 | THEME: WH40K",
            "CHRONO-STAMP: 0918015.M03",
        ]
    if theme_key == "helldivers":
        return [
            f"SUPER EARTH COMMAND BIOS v{version}",
            "Copyright (C) SUPER EARTH MINISTRY OF TRUTH / Managed Democracy Systems",
            "Managed Democracy Tactical Build / Liberty Authorization Line",
            f"DATE: {visible_date}",
            f"SERIAL: SEAF-7851-LIBERTY | BUILD: v{version} | THEME: HELLDIVERS",
        ]
    if theme_key == "arasaka":
        return [
            f"ARASAKA EXECUTIVE SECURITY BIOS v{version}",
            "Copyright (C) ARASAKA CORPORATION / Tactical AI Systems",
            "Corporate Black/Red Security Grid / Executive Tribunal Line",
            f"DATE: {visible_date}",
            f"SERIAL: ARSK-CI-7851 | BUILD: v{version} | THEME: ARASAKA",
        ]
    if theme_key == "janus":
        return [
            f"JANUS DUAL-FRONT BIOS v{version}",
            "Copyright (C) JANUS SECURITY CONSORTIUM / Dual-Front Intelligence",
            "Dual-Face Intelligence Terminal / Mirror Analysis Line",
            f"DATE: {visible_date}",
            f"SERIAL: JANUS-DUAL-7851 | BUILD: v{version} | THEME: JANUS",
        ]
    if theme_key in {"eva", "nerv"}:
        return [
            f"MAGI / NERV BIOS v{version}",
            "Copyright (C) NERV / MAGI Tactical Systems",
            "MAGI Consensus Array / NERV Tactical Interlock Line",
            f"DATE: {visible_date}",
            f"SERIAL: MAGI-NERV-7851 | BUILD: v{version} | THEME: {theme_key.upper()}",
        ]
    return [
        f"EXCOMM WAR ROOM BIOS v{version}",
        "Copyright (C) EXCOMM / CONSENSUS Tactical Systems",
        f"DATE: {visible_date}",
        f"SERIAL: 0xC0A57A71C | BUILD: v{version} | THEME: {theme_key.upper()}",
    ]


def _provider_boot_context(provider_status: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if provider_status is not None:
        payload = provider_status.get("provider", provider_status)
        return payload if isinstance(payload, dict) else {}
    return {
        "status": "unknown",
        "active_backend": "unresolved",
        "base_url": "--",
        "model_count": 0,
        "missing_required_models": {},
        "mock_fallback_enabled": False,
    }


def _provider_post_line(provider_status: Dict[str, Any] | None = None) -> str:
    context = _provider_boot_context(provider_status)
    status = str(context.get("status", "offline")).lower()
    missing_models = context.get("missing_required_models", {}) or {}
    fallback_enabled = bool(context.get("mock_fallback_enabled"))
    if status == "ready":
        return "[OK] Provider Runtime"
    if status == "degraded":
        missing_count = len(missing_models) if hasattr(missing_models, "__len__") else 0
        return f"[WARN] MSTY PROVIDER DEGRADED ({missing_count} missing)"
    if status == "unknown":
        return "[WARN] PROVIDER STATUS UNRESOLVED"
    if fallback_enabled:
        return "[WARN] PROVIDER OFFLINE - MOCK FALLBACK ACTIVE"
    return "[ERROR] MSTY PROVIDER OFFLINE"


def _theme_runtime_label(theme_id: str) -> str:
    theme_key = resolve_theme_key(theme_id)
    labels = {
        "arasaka": "Corporate Runtime",
        "eva": "MAGI Runtime",
        "nerv": "MAGI Runtime",
        "wh40k": "Cogitator Runtime",
        "helldivers": "Democracy Runtime",
        "janus": "Mirror Runtime",
        "military": "Command Runtime",
    }
    return labels.get(theme_key, "Provider Runtime")


def _post_lines(
    theme_id: str,
    provider_status: Dict[str, Any] | None = None,
    rng: random.Random | None = None,
    include_rare: bool = False,
) -> List[str]:
    theme_key = resolve_theme_key(theme_id)
    active_rng = rng or random.Random(TRIBUNAL_PHRASE_SEED)
    lines = list(select_post_checks(theme_id, active_rng, include_rare=include_rare))
    provider_line = _provider_post_line(provider_status)
    if provider_line == "[OK] Provider Runtime":
        provider_line = f"[OK] {_theme_runtime_label(theme_id)}"
    if provider_line not in lines:
        lines.append(provider_line)
    if theme_key == "wh40k":
        for wh40k_line in ("[OK] Machine Spirit Litany", "[OK] NOOSPHERIC TIME INDEX: 0918015.M03"):
            if wh40k_line not in lines:
                lines.append(wh40k_line)
    return list(dict.fromkeys(lines))


def _detected_devices(theme_id: str, rng: random.Random | None = None) -> List[str]:
    active_rng = rng or random.Random(TRIBUNAL_PHRASE_SEED)
    return list(select_detected_devices(theme_id, active_rng))


def _loading_label(theme_id: str) -> str:
    return get_loading_style(theme_id).label


def _dense_rule(title: str, width: int) -> str:
    label = f" {title} "
    remaining = max(4, width - len(label))
    left = remaining // 2
    return ("-" * left) + label + ("-" * (remaining - left))


def _dense_diagnostic_line(name: str, state: str, detail: str, result: str) -> str:
    return f"{name:<23}{state:<12}{detail:<27}{result:>10}"


def _dense_configuration_line(addr: str, psp: str, blocks: str, size: str, owner: str) -> str:
    return f"{addr:<11}{psp:<11}{blocks:>5}{size:>11}   {owner}"


def _dense_subsystem_line(node: str, subsystem: str, value: str, status: str) -> str:
    return f"{node:<28}{subsystem:<28}{value:>10}{status:>14}"


def _dense_owner_name(value: str) -> str:
    normalized = "_".join(value.lower().replace("/", " ").replace("-", " ").split())
    return normalized[:32] or "system_component"


def _dense_configuration_rows(theme_id: str, rng: random.Random) -> List[tuple[str, str, str, str, str]]:
    devices = [_dense_owner_name(device) for device in _detected_devices(theme_id, rng)]
    owners = ["kernel", "terminal_driver", "consensus_bus", *devices]
    rows: List[tuple[str, str, str, str, str]] = []
    for index, row in enumerate(DENSE_CONFIGURATION_ROWS):
        addr, psp, blocks, size, fallback_owner = row
        owner = owners[index] if index < len(owners) else fallback_owner
        rows.append((addr, psp, blocks, size, owner))
    return rows


def _dense_subsystem_rows(theme_id: str) -> List[tuple[str, str, str, str]]:
    theme_key = resolve_theme_key(theme_id)
    theme = THEMES.get(theme_key, THEMES["nerv"])
    rows = [
        (labels["node"][:27], labels["core"][:27], "NOMINAL", "ONLINE")
        for labels in theme.monolith_labels.values()
    ]
    rows.append(("ARBITER", "QUORUM CONTROL", "LOCKED", "ONLINE"))
    return rows


def generate_dense_bios_boot_lines(
    theme_id: str,
    version: str = SYSTEM_VERSION,
    include_logo: bool = True,
    include_loading: bool = True,
    center_logo: bool = False,
    total_memory_mb: int | None = None,
    provider_status: Dict[str, Any] | None = None,
    seed: int | None = None,
    width: int = DEFAULT_BOOT_WIDTH,
) -> List[str]:
    """Build the active dense BIOS layout used by console and Flet startup."""

    theme_key = resolve_theme_key(theme_id)
    theme = THEMES.get(theme_key, THEMES["nerv"])
    active_width = max(80, width)
    rng = random.Random(seed if seed is not None else TRIBUNAL_PHRASE_SEED)
    lines: List[str] = []
    if include_logo:
        logo = _theme_boot_logo_text(theme_key)
        lines.extend([_center_block(logo, active_width) if center_logo else logo, ""])
    lines.extend(_bios_header_lines(theme_key, version))
    lines.extend([f"Chief Architect: {SYSTEM_AUTHOR}", SYSTEM_ORGANIZATION])
    if theme_key == "wh40k":
        lines.append(f"LAST PATCH REF: 0918015.M03 | BUILD: v{version} | MODE: HIGH")
    else:
        lines.append(f"LAST PATCH: {SYSTEM_LAST_PATCH_DATE} | BUILD: v{version} | MODE: HIGH")

    memory_steps, memory_fallback = _memory_steps_mb(total_memory_mb)
    memory_total = memory_steps[-1]
    provider_line = _provider_post_line(provider_status)
    if provider_line.startswith("[OK]"):
        provider_result = "OK"
    elif provider_line.startswith("[ERROR]"):
        provider_result = "ERROR"
    else:
        provider_result = "WARN"
    provider_detail = _theme_runtime_label(theme_key).upper()
    diagnostic_rows = [
        ("CO-CPU", "CHECK", "256 SEGMENTS", "OK"),
        ("MEMORY BANK", "CHECK", f"{memory_total:06d} MB" + (" FALLBACK" if memory_fallback else ""), "OK"),
        ("I/O VECTORS", "CHECK", theme.boot_profile_id.upper(), "OK"),
        ("CONSOLE DRIVERS", "CHECK", "VT-09 / UTF-8", "OK"),
        ("ROUTING TABLES", "CHECK", "12 CHANNELS", "OK"),
        ("STATUS ANALYZER", "CHECK", theme.panel_style.upper()[:24], "OK"),
        ("SECURITY INTERLOCK", "CHECK", theme.border_style.upper()[:24], "OK"),
        ("THEME RUNTIME", "CHECK", provider_detail[:24], provider_result),
    ]
    lines.extend(
        [
            "",
            _dense_rule("SYSTEM DIAGNOSTICS", active_width),
            _dense_diagnostic_line("DEVICE", "STATE", "PARAMETERS", "RESULT"),
            _dense_diagnostic_line("-" * 18, "-" * 7, "-" * 18, "-" * 6),
        ]
    )
    lines.extend(_dense_diagnostic_line(*row) for row in diagnostic_rows)
    lines.extend(
        [
            "",
            _dense_rule("CONSENSUS SYSTEM CONFIGURATION", active_width),
            _dense_configuration_line("ADDR", "PSP", "BLKS", "SIZE", "OWNER / PARAMETERS"),
            _dense_configuration_line("-" * 5, "-" * 4, "-" * 4, "-" * 4, "-" * 18),
        ]
    )
    lines.extend(_dense_configuration_line(*row) for row in _dense_configuration_rows(theme_key, rng))
    lines.extend(
        [
            "",
            _dense_rule(theme.display_name.upper(), active_width),
            _dense_subsystem_line("NODE", "SUBSYSTEM", "VALUE", "STATUS"),
            _dense_subsystem_line("-" * 12, "-" * 14, "-" * 7, "-" * 8),
        ]
    )
    lines.extend(_dense_subsystem_line(*row) for row in _dense_subsystem_rows(theme_key))
    lines.extend(["", DENSE_SUMMARY_LINES[theme_key]])

    if include_loading:
        style = get_loading_style(theme_key)
        lines.extend(["", style.label])
        lines.extend(f"[LOAD] {stage}" for stage in style.stages)
        lines.extend(
            [
                format_loading_bar(theme_key, 100),
                DENSE_READY_LINES[theme_key],
                "HANDOFF TO MAIN INTERFACE",
            ]
        )
    return lines


def generate_bios_boot_lines(
    theme_id: str,
    version: str = SYSTEM_VERSION,
    include_logo: bool = True,
    include_loading: bool = True,
    center_logo: bool = False,
    total_memory_mb: int | None = None,
    provider_status: Dict[str, Any] | None = None,
    randomize_phrases: bool = False,
    seed: int | None = None,
) -> List[str]:
    theme_key = resolve_theme_key(theme_id)
    lines: List[str] = []
    if include_logo:
        logo = _theme_boot_logo_text(theme_id)
        lines.extend([_center_block(logo) if center_logo else logo, ""])
    header_lines = _bios_header_lines(theme_id, version)
    lines.extend([*(_center_lines_block(header_lines) if center_logo else header_lines), ""])
    memory_steps, memory_fallback = _memory_steps_mb(total_memory_mb)
    for amount in memory_steps:
        lines.append(f"Memory Test: {amount:06d} MB OK")
    if memory_fallback:
        lines.append("Memory Source: FALLBACK CONFIGURATION")
    phrase_rng = random.Random(seed if randomize_phrases else TRIBUNAL_PHRASE_SEED)
    lines.extend(["", "Detecting devices:"])
    lines.extend(f"- {device}" for device in _detected_devices(theme_id, phrase_rng))
    lines.extend(["", *_center_lines_block(["POST:", *_post_lines(theme_id, provider_status, phrase_rng, randomize_phrases)])])
    lines.extend(["", *_center_lines_block(["Tribunal initialization:", *node_boot_lines(theme_id, phrase_rng)])])
    lines.extend(
        [
            "",
            "WAR ROOM INIT PROTOCOL COMPLETE",
            "TRANSFERRING CONTROL TO CONSENSUS LOADER...",
        ]
    )
    if include_loading:
        style = get_loading_style(theme_id)
        lines.extend(["", style.label, f"[LOAD:{style.key}] {style.sample_phrase}"])
        lines.extend(f"[LOAD] {stage}" for stage in style.stages)
        lines.extend([format_loading_bar(theme_key, style.sample_percent), "HANDOFF TO MAIN INTERFACE"])
    return lines


def _delay_for(speed: str, rng: random.Random | None = None) -> float:
    normalized = speed.lower()
    if normalized == "random":
        active_rng = rng or random.Random()
        return active_rng.uniform(*RANDOM_DELAY_RANGE)
    return SPEED_DELAYS.get(normalized, SPEED_DELAYS["normal"])


def _clear_console() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _print_with_cursor(line: str, delay: float) -> None:
    if not line:
        print()
        time.sleep(delay)
        return
    print(line)
    sys.stdout.write("_\r")
    sys.stdout.flush()
    time.sleep(delay)
    sys.stdout.write(" \r")
    sys.stdout.flush()


def _line_status_color(line: str) -> str:
    try:
        from colorama import Fore  # type: ignore
    except Exception:
        return ""
    if "[WARN]" in line or "[ERROR]" in line or "OFFLINE" in line:
        return Fore.LIGHTRED_EX
    if "[OK]" in line or "ONLINE" in line:
        return Fore.LIGHTGREEN_EX
    return ""


def _type_with_cursor(line: str, delay: float) -> None:
    if not line:
        print()
        time.sleep(delay)
        return
    color = _line_status_color(line)
    reset = _reset_console_color() if color else ""
    prefix_len = len(line) - len(line.lstrip(" "))
    sys.stdout.write(line[:prefix_len])
    for char in line[prefix_len:]:
        sys.stdout.write(f"{color}{char}{reset}" if color else char)
        sys.stdout.flush()
        time.sleep(max(delay / 18, 0.002))
    print()
    sys.stdout.write("_\r")
    sys.stdout.flush()
    time.sleep(max(delay / 2, 0.008))
    sys.stdout.write(" \r")
    sys.stdout.flush()


def _stdout_can_encode(text: str) -> bool:
    encoding = sys.stdout.encoding or "utf-8"
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def _console_safe_text(text: str) -> str:
    replacements = str.maketrans(
        {
            "█": "#",
            "▓": "#",
            "▒": "-",
            "░": "-",
            "■": "#",
            "□": "-",
            "▰": "#",
            "▱": "-",
            "═": "=",
            "║": "|",
            "╔": "+",
            "╗": "+",
            "╚": "+",
            "╝": "+",
            "╠": "+",
            "╣": "+",
            "╦": "+",
            "╩": "+",
            "╬": "+",
        }
    )
    translated = text.translate(replacements)
    encoding = sys.stdout.encoding or "utf-8"
    return translated.encode(encoding, errors="replace").decode(encoding, errors="replace")


def _ansi_color(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return f"\x1b[38;2;{red};{green};{blue}m"


def _boot_color_values(theme_id: str) -> Dict[str, str]:
    theme_key = resolve_theme_key(theme_id)
    theme = THEMES.get(theme_key, THEMES["nerv"])
    data_color = theme.secondary_text or theme.secondary_color
    success_color = theme.accent_color
    logo_color = theme.primary_color
    if theme_key == "arasaka":
        data_color = "#c7c7c7"
        success_color = "#ffffff"
    elif theme_key in {"eva", "nerv"}:
        success_color = "#008fbd"
        logo_color = "#7a0018"
    return {
        "logo": logo_color,
        "primary": theme.primary_color,
        "data": data_color,
        "success": success_color,
        "text": theme.text_color,
        "warning": theme.warning_color,
    }


def _boot_terminal_palette(theme_id: str) -> BootTerminalPalette:
    try:
        from colorama import just_fix_windows_console  # type: ignore

        just_fix_windows_console()
    except Exception:
        pass
    colors = _boot_color_values(theme_id)
    return BootTerminalPalette(
        logo=_ansi_color(colors["logo"]),
        primary=_ansi_color(colors["primary"]),
        data=_ansi_color(colors["data"]),
        success=_ansi_color(colors["success"]),
        text=_ansi_color(colors["text"]),
        warning=_ansi_color(colors["warning"]),
        reset="\x1b[0m",
    )


def _logo_console_color(theme_id: str) -> str:
    return _boot_terminal_palette(theme_id).logo


def _reset_console_color() -> str:
    return "\x1b[0m"


def _print_logo_with_cursor(logo: str, theme_id: str, delay: float) -> None:
    color = _logo_console_color(theme_id)
    reset = _reset_console_color() if color else ""
    if not _stdout_can_encode(logo):
        logo = _console_safe_text(logo)
    for subline in logo.splitlines() or [""]:
        _print_with_cursor(f"{color}{subline}{reset}" if color else subline, delay)


def _render_lines(lines: Iterable[str], delay: float) -> None:
    for line in lines:
        for subline in line.splitlines() or [""]:
            if "[OK]" in subline or "[WARN]" in subline or "ONLINE" in subline or "OFFLINE" in subline:
                _type_with_cursor(subline, delay)
                if "ONLINE" in subline:
                    time.sleep(delay * 1.8)
                elif "[WARN]" in subline:
                    time.sleep(delay * 1.3)
            else:
                _print_with_cursor(subline, delay)


def _dense_styled_segments(line: str, palette: BootTerminalPalette) -> List[tuple[str, str]]:
    stripped = line.strip()
    if not stripped:
        return [(palette.text, line)]
    if "BIOS v" in stripped or stripped.startswith("-"):
        return [(palette.primary, line)]
    if stripped.startswith(("INITIALIZING", "AUTHORIZING", "AWAKENING", "[LOAD]")):
        return [(palette.primary, line)]
    if "[" in stripped and "]" in stripped and "%" in stripped:
        return [(palette.primary, line)]
    if stripped.endswith((" READY", " AWAKENED")) or stripped in {
        "HANDOFF TO MAIN INTERFACE",
        "TRANSFERRING CONTROL TO WAR ROOM...",
    }:
        return [(palette.success, line)]
    if "WARN" in stripped or "ERROR" in stripped or stripped.endswith(("WARN", "ERROR")):
        return [(palette.warning, line)]
    if stripped.startswith(
        (
            "Copyright",
            "MAGI Consensus Array",
            "Adeptus Mechanicus",
            "Managed Democracy",
            "Corporate Black/Red",
            "Dual-Face Intelligence",
            "DATE",
            "SERIAL:",
            "Chief Architect:",
            "Janus Securitek",
            "LAST PATCH",
        )
    ):
        return [(palette.text, line)]
    for status in ("ONLINE", "OK"):
        if stripped.endswith(status):
            split_at = line.rfind(status)
            return [(palette.data, line[:split_at]), (palette.success, line[split_at:])]
    if stripped.startswith(("DEVICE", "ADDR", "NODE")):
        return [(palette.text, line)]
    return [(palette.data, line)]


def _type_dense_line(line: str, delay: float, palette: BootTerminalPalette) -> None:
    if not line:
        print()
        time.sleep(delay)
        return
    character_delay = max(0.0008, delay * 0.06)
    burst_size = max(1, round(MIN_RENDER_SLEEP / character_delay))
    for color, text in _dense_styled_segments(line, palette):
        sys.stdout.write(color)
        for offset in range(0, len(text), burst_size):
            burst = text[offset : offset + burst_size]
            sys.stdout.write(burst)
            sys.stdout.flush()
            time.sleep(max(MIN_RENDER_SLEEP, character_delay * len(burst)))
    sys.stdout.write(palette.reset + "\n")
    sys.stdout.flush()
    time.sleep(delay)


def _render_dense_lines(lines: Iterable[str], theme_id: str, delay: float) -> None:
    palette = _boot_terminal_palette(theme_id)
    for line in lines:
        for subline in line.splitlines() or [""]:
            _type_dense_line(subline, delay, palette)


def _flet_dense_line_color(theme_id: str, line: str) -> str:
    colors = _boot_color_values(theme_id)
    stripped = line.strip()
    if "BIOS v" in stripped or stripped.startswith("-"):
        return colors["primary"]
    if stripped.endswith(("ONLINE", "OK", " READY", " AWAKENED")) or stripped == "HANDOFF TO MAIN INTERFACE":
        return colors["success"]
    if "WARN" in stripped or "ERROR" in stripped:
        return colors["warning"]
    if stripped.startswith(("DEVICE", "ADDR", "NODE", "Copyright", "DATE", "SERIAL", "Chief", "Janus", "LAST PATCH")):
        return colors["text"]
    return colors["data"]


def _render_runtime_diagnostics(theme_id: str, delay: float, rng: random.Random) -> None:
    theme_key = resolve_theme_key(theme_id)
    prefixes = {
        "military": "EXCOMM",
        "eva": "MAGI",
        "nerv": "NERV",
        "wh40k": "COGITATOR",
        "helldivers": "SEAF",
        "arasaka": "ARASAKA",
        "janus": "JANUS",
    }
    checksum = f"0x{rng.randrange(0x100000, 0xFFFFFF):06X}"
    _print_with_cursor(f"{prefixes.get(theme_key, 'CONSENSUS')} CHECKSUM: {checksum}", delay)
    time.sleep(delay * 1.4)
    _type_with_cursor("[WARN] AUX CHANNEL RECALIBRATING", delay)
    time.sleep(delay * 1.8)
    _type_with_cursor("[OK] AUX CHANNEL LOCKED", delay)


def await_user_interaction(stdin=None) -> None:
    active_stdin = stdin or sys.stdin
    prompt = "PRESS ENTER TO ENTER THE WAR ROOM"
    print(_center(prompt))
    if active_stdin.isatty():
        active_stdin.readline()


def render_bios_boot_console(
    theme_id: str = "NERV",
    speed: str = "random",
    seed: int | None = None,
    provider_status: Dict[str, Any] | None = None,
) -> None:
    rng = random.Random(seed)
    delay = _delay_for(speed, rng)
    _clear_console()
    logo = _center_block(_theme_boot_logo_text(theme_id))
    dense_lines = generate_dense_bios_boot_lines(
        theme_id,
        SYSTEM_VERSION,
        include_logo=False,
        include_loading=False,
        provider_status=provider_status,
        seed=seed,
        width=_terminal_width(),
    )

    _print_logo_with_cursor(logo, theme_id, delay)
    time.sleep(max(0.4, delay * 12))
    _clear_console()
    _render_dense_lines(dense_lines, theme_id, delay)
    print()
    render_loading_console(theme_id, speed=speed, seed=seed)
    _render_dense_lines((DENSE_READY_LINES[resolve_theme_key(theme_id)],), theme_id, delay)
    await_user_interaction()
    _render_dense_lines(("HANDOFF TO MAIN INTERFACE",), theme_id, delay)


def render_bios_boot_flet(
    page,
    theme_id: str = "NERV",
    speed: str = "normal",
    seed: int | None = None,
    provider_status: Dict[str, Any] | None = None,
) -> None:
    lines = generate_dense_bios_boot_lines(
        theme_id,
        SYSTEM_VERSION,
        center_logo=True,
        provider_status=provider_status,
        seed=seed,
    )
    if "HANDOFF TO MAIN INTERFACE" in lines:
        handoff_index = lines.index("HANDOFF TO MAIN INTERFACE")
        lines.insert(handoff_index, "PRESS ENTER TO ENTER THE WAR ROOM")
    else:
        lines.append("PRESS ENTER TO ENTER THE WAR ROOM")
    theme_key = resolve_theme_key(theme_id)
    theme = THEMES.get(theme_key, THEMES["nerv"])
    boot_colors = _boot_color_values(theme_key)
    delay = _delay_for(speed, random.Random(seed))
    try:
        import flet as ft  # type: ignore

        for index, line in enumerate(lines):
            page.add(
                ft.Text(
                    line,
                    font_family=theme.font_family,
                    color=boot_colors["logo"] if index == 0 else _flet_dense_line_color(theme_key, line),
                    text_align=ft.TextAlign.CENTER if index == 0 else ft.TextAlign.LEFT,
                    selectable=False,
                    no_wrap=False,
                )
            )
            page.update()
            time.sleep(delay)
    except Exception:
        for line in lines:
            if hasattr(page, "add"):
                page.add(line)
            if hasattr(page, "update"):
                page.update()
            time.sleep(delay)
