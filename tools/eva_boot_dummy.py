from __future__ import annotations

import argparse
import os
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
from ui.animations.bios_boot import _bios_header_lines, _boot_color_values, _theme_boot_logo_text
from ui.animations.loading import format_loading_bar, get_loading_style
from ui.boot.registry import boot_registry_for_theme
from ui.themes.catalog import THEMES, resolve_theme_key


AUTHOR_LINE = "Chief Architect: Erhardt Von Grupten Mundt"
ORGANIZATION_LINE = "Janus Securitek Consortium / CONSENSUS Tactical Systems"
DEFAULT_WIDTH = 100
SUPPORTED_THEME_KEYS = ("eva", "arasaka", "military", "wh40k", "helldivers", "janus")

SPEEDS = {
    # character delay, completed-line delay, centered-logo hold
    "fast": (0.0010, 0.012, 0.40),
    "normal": (0.0030, 0.030, 0.95),
    "slow": (0.0060, 0.060, 1.50),
}
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


@dataclass(frozen=True)
class EvaPalette:
    """Terminal palette fields retained for compatibility with the EVA prototype tests."""

    orange: str = ""  # theme primary
    red: str = ""  # theme secondary
    cyan: str = ""  # theme accent
    white: str = ""  # theme text
    reset: str = ""
    logo: str = ""


def _default_patch_date() -> str:
    return SYSTEM_LAST_PATCH_DATE


def _terminal_width(requested: int | None = None) -> int:
    if requested is not None:
        return max(80, requested)
    return max(80, shutil.get_terminal_size((DEFAULT_WIDTH, 30)).columns)


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


def _diagnostic_rows(theme_key: str) -> list[tuple[str, str, str, str]]:
    theme = THEMES[theme_key]
    registry = boot_registry_for_theme(theme_key)
    runtime = registry.post_checks[0].removeprefix("[OK] ")
    return [
        ("CO-CPU", "CHECK", "256 SEGMENTS", "OK"),
        ("I/O VECTORS", "CHECK", theme.boot_profile_id.upper(), "OK"),
        ("CONSOLE DRIVERS", "CHECK", "VT-09 / UTF-8", "OK"),
        ("ROUTING TABLES", "CHECK", "12 CHANNELS", "OK"),
        ("STATUS ANALYZER", "CHECK", theme.panel_style.upper()[:24], "OK"),
        ("SECURITY INTERLOCK", "CHECK", theme.border_style.upper()[:24], "OK"),
        ("THEME RUNTIME", "CHECK", runtime.upper()[:24], "OK"),
    ]


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


def build_theme_dummy_lines(
    theme_id: str,
    *,
    width: int = DEFAULT_WIDTH,
    patch_date: str | None = None,
    unicode: bool = True,
) -> list[str]:
    theme_key = resolve_theme_key(theme_id)
    if theme_key not in SUPPORTED_THEME_KEYS:
        raise ValueError(f"Unsupported prototype theme: {theme_id}")
    theme = THEMES[theme_key]
    active_width = _terminal_width(width)
    patch = patch_date or _default_patch_date()
    logo = _theme_boot_logo_text(theme_key)
    header = _bios_header_lines(theme_key, SYSTEM_VERSION)
    loading = get_loading_style(theme_key)

    lines = [*_center_block(logo, active_width), ""]
    lines.extend(header)
    lines.extend(
        [
            AUTHOR_LINE,
            ORGANIZATION_LINE,
            f"LAST PATCH: {patch} | BUILD: v{SYSTEM_VERSION} | MODE: HIGH",
            "",
            _rule("SYSTEM DIAGNOSTICS", active_width),
            _diagnostic_line("DEVICE", "STATE", "PARAMETERS", "RESULT"),
            _diagnostic_line("-" * 18, "-" * 7, "-" * 18, "-" * 6),
        ]
    )
    lines.extend(_diagnostic_line(*row) for row in _diagnostic_rows(theme_key))
    lines.extend(
        [
            "",
            _rule("CONSENSUS SYSTEM CONFIGURATION", active_width),
            _configuration_line("ADDR", "PSP", "BLKS", "SIZE", "OWNER / PARAMETERS"),
            _configuration_line("-" * 5, "-" * 4, "-" * 4, "-" * 4, "-" * 18),
        ]
    )
    lines.extend(_configuration_line(*row) for row in _configuration_rows(theme_key))
    lines.extend(
        [
            "",
            _rule(theme.display_name.upper(), active_width),
            _subsystem_line("NODE", "SUBSYSTEM", "VALUE", "STATUS"),
            _subsystem_line("-" * 12, "-" * 14, "-" * 7, "-" * 8),
        ]
    )
    lines.extend(_subsystem_line(*row) for row in _subsystem_rows(theme_key))
    lines.extend(
        [
            "",
            SUMMARY_LINES[theme_key],
            "",
            loading.label,
            format_theme_loading_bar(theme_key, 100, unicode=unicode),
            READY_LINES[theme_key],
            "TRANSFERRING CONTROL TO WAR ROOM...",
        ]
    )
    return lines


def build_eva_dummy_lines(
    *,
    width: int = DEFAULT_WIDTH,
    patch_date: str | None = None,
    unicode: bool = True,
) -> list[str]:
    return build_theme_dummy_lines("eva", width=width, patch_date=patch_date, unicode=unicode)


def _stdout_supports(text: str) -> bool:
    encoding = sys.stdout.encoding or "utf-8"
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def _ansi_color(hex_color: str) -> str:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return f"\x1b[38;2;{red};{green};{blue}m"


def _palette(enabled: bool, theme_id: str = "eva") -> EvaPalette:
    if not enabled:
        return EvaPalette()
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
        reset="\x1b[0m",
        logo=_ansi_color(colors["logo"]),
    )


def _clear(enabled: bool) -> None:
    if enabled:
        os.system("cls" if os.name == "nt" else "clear")


def _styled_segments(line: str, palette: EvaPalette) -> list[tuple[str, str]]:
    if not palette.reset:
        return [("", line)]
    stripped = line.strip()
    if not stripped:
        return [(palette.white, line)]
    if "BIOS v" in stripped or stripped.startswith("-"):
        return [(palette.orange, line)]
    if ("[" in stripped and "]" in stripped and "%" in stripped) or stripped.startswith("INITIALIZING"):
        return [(palette.orange, line)]
    if stripped.endswith((" READY", " AWAKENED")) or stripped == "TRANSFERRING CONTROL TO WAR ROOM...":
        return [(palette.cyan, line)]
    if stripped.startswith(("Copyright", "MAGI Consensus Array", "DATE", "SERIAL:", "Chief Architect:", "Janus ", "LAST PATCH:")):
        return [(palette.white, line)]
    for status in ("ONLINE", "OK"):
        if stripped.endswith(status):
            split_at = line.rfind(status)
            return [(palette.red, line[:split_at]), (palette.cyan, line[split_at:])]
    if stripped.startswith(("DEVICE", "ADDR", "NODE")):
        return [(palette.white, line)]
    return [(palette.red, line)]


def _write_styled_line(line: str, palette: EvaPalette) -> None:
    for color, text in _styled_segments(line, palette):
        if color:
            sys.stdout.write(color)
        sys.stdout.write(text)
    if palette.reset:
        sys.stdout.write(palette.reset)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _type_styled_line(line: str, char_delay: float, line_delay: float, palette: EvaPalette) -> None:
    if not line:
        print()
        time.sleep(line_delay)
        return
    for color, text in _styled_segments(line, palette):
        if color:
            sys.stdout.write(color)
        burst_size = max(1, round(MIN_RENDER_SLEEP / char_delay))
        for offset in range(0, len(text), burst_size):
            burst = text[offset : offset + burst_size]
            sys.stdout.write(burst)
            sys.stdout.flush()
            time.sleep(max(MIN_RENDER_SLEEP, char_delay * len(burst)))
    if palette.reset:
        sys.stdout.write(palette.reset)
    sys.stdout.write("\n")
    sys.stdout.flush()
    time.sleep(line_delay)


def _print_lines(lines: Iterable[str], delay: float, color: str, reset: str) -> None:
    for line in lines:
        print(f"{color}{line}{reset}" if color else line)
        if delay:
            time.sleep(delay)


def _print_styled_lines(lines: Iterable[str], palette: EvaPalette) -> None:
    for line in lines:
        _write_styled_line(line, palette)


def _type_styled_lines(
    lines: Iterable[str],
    char_delay: float,
    line_delay: float,
    palette: EvaPalette,
) -> None:
    for line in lines:
        _type_styled_line(line, char_delay, line_delay, palette)


def render_theme_dummy(
    theme_id: str,
    *,
    speed: str = "normal",
    patch_date: str | None = None,
    width: int | None = None,
    clear: bool = True,
    color: bool = True,
) -> None:
    theme_key = resolve_theme_key(theme_id)
    active_width = _terminal_width(width)
    char_delay, line_delay, logo_hold = SPEEDS[speed]
    palette = _palette(color, theme_key)
    unicode = _stdout_supports("■□")
    logo_lines = _center_block(_theme_boot_logo_text(theme_key), active_width)
    loading_label = get_loading_style(theme_key).label

    _clear(clear)
    _print_lines(logo_lines, line_delay, palette.logo, palette.reset)
    time.sleep(logo_hold)
    _clear(clear)

    static_lines = build_theme_dummy_lines(
        theme_key,
        width=active_width,
        patch_date=patch_date,
        unicode=unicode,
    )
    body_start = len(logo_lines) + 1
    body = static_lines[body_start:]
    loading_index = body.index(loading_label)
    _type_styled_lines(body[: loading_index + 1], char_delay, line_delay, palette)

    for percent in range(0, 101, 4):
        bar = format_theme_loading_bar(theme_key, percent, unicode=unicode)
        if palette.orange:
            sys.stdout.write(f"\r{palette.orange}{bar}{palette.reset}")
        else:
            sys.stdout.write(f"\r{bar}")
        sys.stdout.flush()
        time.sleep(max(line_delay * 1.8, 0.025))
    print()
    _type_styled_lines(body[loading_index + 2 :], char_delay * 1.5, line_delay * 2, palette)


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
    parser.add_argument("--patch-date", default=None, help="Override LAST PATCH (YYYY-MM-DD).")
    parser.add_argument("--width", type=int, default=None, help="Preview width; minimum 80 columns.")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear the terminal between stages.")
    parser.add_argument("--no-color", action="store_true", help="Disable terminal theme colors.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    theme_key = resolve_theme_key(args.theme)
    width = _terminal_width(args.width)
    unicode = _stdout_supports("■□")
    if args.static:
        palette = _palette(not args.no_color, theme_key)
        _print_styled_lines(
            build_theme_dummy_lines(theme_key, width=width, patch_date=args.patch_date, unicode=unicode),
            palette,
        )
        return 0
    render_theme_dummy(
        theme_key,
        speed=args.speed,
        patch_date=args.patch_date,
        width=width,
        clear=not args.no_clear,
        color=not args.no_color,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
