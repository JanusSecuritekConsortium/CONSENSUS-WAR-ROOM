from __future__ import annotations

import os
import random
import shutil
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List

from config.version import SYSTEM_VERSION
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
        logo = _theme_logo_text(theme_id).rstrip("\n")
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


def _logo_console_color(theme_id: str) -> str:
    theme_key = resolve_theme_key(theme_id)
    try:
        from colorama import Fore, init  # type: ignore

        init()
    except Exception:
        return ""
    colors = {
        "military": Fore.LIGHTGREEN_EX,
        "eva": Fore.LIGHTRED_EX,
        "nerv": Fore.LIGHTRED_EX,
        "wh40k": Fore.YELLOW,
        "helldivers": Fore.LIGHTBLUE_EX,
        "arasaka": Fore.LIGHTRED_EX,
        "janus": Fore.LIGHTMAGENTA_EX,
    }
    return colors.get(theme_key, "")


def _reset_console_color() -> str:
    try:
        from colorama import Style  # type: ignore
    except Exception:
        return ""
    return Style.RESET_ALL


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
    logo = _center_block(_theme_logo_text(theme_id))
    header_and_checks = generate_bios_boot_lines(
        theme_id,
        SYSTEM_VERSION,
        include_logo=False,
        include_loading=False,
        provider_status=provider_status,
        randomize_phrases=True,
        seed=seed,
    )

    _print_logo_with_cursor(logo, theme_id, delay)
    _print_with_cursor("", delay)
    _render_lines(header_and_checks, delay)
    _render_runtime_diagnostics(theme_id, delay, rng)
    _print_with_cursor("", delay)
    render_loading_console(theme_id, speed=speed, seed=seed)
    await_user_interaction()
    _render_lines(("HANDOFF TO MAIN INTERFACE",), delay)


def render_bios_boot_flet(
    page,
    theme_id: str = "NERV",
    speed: str = "normal",
    seed: int | None = None,
    provider_status: Dict[str, Any] | None = None,
) -> None:
    lines = generate_bios_boot_lines(
        theme_id,
        SYSTEM_VERSION,
        center_logo=True,
        provider_status=provider_status,
        randomize_phrases=True,
        seed=seed,
    )
    if "HANDOFF TO MAIN INTERFACE" in lines:
        handoff_index = lines.index("HANDOFF TO MAIN INTERFACE")
        lines.insert(handoff_index, "PRESS ENTER TO ENTER THE WAR ROOM")
    else:
        lines.append("PRESS ENTER TO ENTER THE WAR ROOM")
    theme_key = resolve_theme_key(theme_id)
    theme = THEMES.get(theme_key, THEMES["nerv"])
    delay = _delay_for(speed, random.Random(seed))
    try:
        import flet as ft  # type: ignore

        for index, line in enumerate(lines):
            page.add(
                ft.Text(
                    line,
                    font_family=theme.font_family,
                    color=theme.primary_color if index == 0 else theme.text_color,
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
