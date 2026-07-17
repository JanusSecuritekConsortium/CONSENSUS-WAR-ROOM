from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass
from typing import Dict, List

from core.models import Theme
from ui.themes.boot_profiles import get_boot_profile
from ui.themes.catalog import THEMES, resolve_theme_key


@dataclass(frozen=True)
class LoadingStyle:
    key: str
    theme_key: str
    label: str
    sample_phrase: str
    stages: List[str]
    sample_percent: int


LOADING_STYLES: Dict[str, LoadingStyle] = {
    "military": LoadingStyle(
        key="tactical_green_bar",
        theme_key="military",
        label="INITIALIZING EXCOMM WAR ROOM",
        sample_phrase="TACTICAL GREEN BAR",
        stages=["SYSTEM CHECK", "COMMS", "MONOLITH LINK", "TACTICAL BUS"],
        sample_percent=66,
    ),
    "eva": LoadingStyle(
        key="magi_sync_rate",
        theme_key="eva",
        label="INITIALIZING MAGI CONSENSUS ARRAY",
        sample_phrase="MAGI-LINK SYNCHRONIZATION",
        stages=["MAGI LINK", "SYNCHRONIZATION RATE", "PATTERN ANALYSIS", "INTERLOCK BUS"],
        sample_percent=72,
    ),
    "nerv": LoadingStyle(
        key="nerv_magi_interlock",
        theme_key="nerv",
        label="INITIALIZING NERV MAGI INTERLOCK",
        sample_phrase="NERV MAGI-LINK INTERLOCK",
        stages=["MAGI LINK", "SYNCHRONIZATION RATE", "PATTERN ANALYSIS", "INTERLOCK BUS"],
        sample_percent=72,
    ),
    "wh40k": LoadingStyle(
        key="cogitator_litany",
        theme_key="wh40k",
        label="AWAKENING IMPERIAL COGITATOR",
        sample_phrase="COGITATOR RITE AND LITANY",
        stages=["MACHINE SPIRIT", "NOOSPHERIC LINK", "DATA-VAULT", "SANCTION PROTOCOL"],
        sample_percent=70,
    ),
    "helldivers": LoadingStyle(
        key="managed_democracy",
        theme_key="helldivers",
        label="AUTHORIZING MANAGED DEMOCRACY INTERFACE",
        sample_phrase="LIBERTY AND DEMOCRACY BAR",
        stages=["DEMOCRATIC AUTHORIZATION", "LIBERTY LOGIC", "REQUISITION ACCOUNTING", "STRATAGEM SAFETY"],
        sample_percent=71,
    ),
    "arasaka": LoadingStyle(
        key="corporate_clearance_grid",
        theme_key="arasaka",
        label="INITIALIZING ARASAKA EXECUTIVE GRID",
        sample_phrase="CORPORATE CLEARANCE GRID",
        stages=["SECURITY CLEARANCE", "COUNTERINTELLIGENCE GRID", "CORPORATE NODE", "BOARD VERDICT CHANNEL"],
        sample_percent=60,
    ),
    "janus": LoadingStyle(
        key="dual_front_mirror",
        theme_key="janus",
        label="INITIALIZING JANUS MIRROR CHANNEL",
        sample_phrase="DUAL-FRONT MIRROR SYNC",
        stages=["DUAL CHANNEL", "ANALYTIC MIRROR", "COUNTERPART SYNC", "REVERSIBILITY CHECK"],
        sample_percent=62,
    ),
}


def get_loading_style(theme_id: str) -> LoadingStyle:
    theme_key = resolve_theme_key(theme_id)
    try:
        return LOADING_STYLES[theme_key]
    except KeyError as exc:
        raise RuntimeError(f"Unknown loading style for theme: {theme_id}") from exc


def loading_delay(speed: str, seed: int | None = None) -> float:
    normalized = speed.lower()
    fixed = {"fast": 0.012, "normal": 0.03, "slow": 0.07}
    if normalized in fixed:
        return fixed[normalized]
    rng = random.Random(seed)
    return rng.uniform(0.015, 0.06)


def _delay_for_step(speed: str, rng: random.Random) -> float:
    normalized = speed.lower()
    fixed = {"fast": 0.012, "normal": 0.03, "slow": 0.07}
    if normalized in fixed:
        return fixed[normalized]
    return rng.uniform(0.015, 0.06)


def _fill(width: int, percent: int, filled_char: str, empty_char: str) -> str:
    filled = max(0, min(width, width * percent // 100))
    return filled_char * filled + empty_char * (width - filled)


def _mirrored_fill(width: int, percent: int, filled_char: str, empty_char: str) -> str:
    bounded = max(0, min(100, percent))
    filled = width * bounded // 100
    left = (filled + 1) // 2
    right = filled // 2
    middle = width - left - right
    return (filled_char * left) + (empty_char * middle) + (filled_char * right)


def format_loading_bar(theme_id: str, percent: int, ascii_only: bool = False) -> str:
    theme_key = resolve_theme_key(theme_id)
    percent = max(0, min(100, percent))
    if theme_key == "military":
        return f"TACTICAL [{_fill(24, percent, '#', '-')}] {percent:3d}%"
    if theme_key == "eva":
        if ascii_only:
            return f"MAGI-LINK <{_fill(18, percent, '|', '.')}> {percent:3d}%"
        return f"MAGI-LINK <{_fill(18, percent, '■', '□')}> {percent:3d}%"
    if theme_key == "nerv":
        if ascii_only:
            return f"NERV-INTERLOCK ||{_fill(18, percent, '#', '.')}|| {percent:3d}%"
        return f"NERV-INTERLOCK ||{_fill(18, percent, '▰', '▱')}|| {percent:3d}%"
    if theme_key == "arasaka":
        if ascii_only:
            return f"SECURITY CLEARANCE ||{_fill(14, percent, '#', '-')}|| {percent:3d}%"
        return f"SECURITY CLEARANCE ||{_fill(14, percent, '█', '░')}|| {percent:3d}%"
    if theme_key == "janus":
        filled_char = "#" if ascii_only else "▓"
        empty_char = "." if ascii_only else "░"
        return f"DUAL-CHANNEL SYNC <{_mirrored_fill(16, percent, filled_char, empty_char)}> {percent:3d}%"
    if theme_key == "wh40k":
        if ascii_only:
            return f"MACHINE-SPIRIT PURITY {{{_fill(12, percent, '#', ':')}}} {percent:3d}%"
        return f"MACHINE-SPIRIT PURITY {{{_fill(12, percent, '▓', '▒')}}} {percent:3d}%"
    if theme_key == "helldivers":
        if ascii_only:
            return f"DEMOCRATIC AUTHORIZATION >>>{_fill(12, percent, '>', '-')}<<< {percent:3d}%"
        return f"DEMOCRATIC AUTHORIZATION >>>{_fill(12, percent, '▶', '·')}<<< {percent:3d}%"
    return f"[{_fill(24, percent, '#', '-')}] {percent:3d}%"


def build_loading_sample_text(theme: Theme, width: int = 32, ascii_only: bool = False) -> str:
    profile = get_boot_profile(theme.boot_profile_id)
    style = get_loading_style(theme.key)
    lines = [
        f"[LOAD:{style.key}] {style.sample_phrase}",
        format_loading_bar(theme.key, style.sample_percent, ascii_only=ascii_only),
    ]
    for line in style.stages:
        lines.append(f"[STAGE] {line}")
    for line in profile.status_lines:
        if line not in style.stages:
            lines.append(f"[STATUS] {line}")
    return "\n".join(lines) + "\n"


def render_loading_sample(theme: Theme, width: int = 32) -> None:
    sample = build_loading_sample_text(theme, width=width)
    if not _stdout_can_encode(sample):
        sample = build_loading_sample_text(theme, width=width, ascii_only=True)
    print(sample)


def _stdout_can_encode(text: str) -> bool:
    encoding = sys.stdout.encoding or "utf-8"
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def _terminal_loading_color(theme_id: str) -> tuple[str, str]:
    try:
        from colorama import just_fix_windows_console  # type: ignore

        just_fix_windows_console()
    except Exception:
        pass
    theme = THEMES[resolve_theme_key(theme_id)]
    value = theme.primary_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return f"\x1b[38;2;{red};{green};{blue}m", "\x1b[0m"


def render_loading_console(theme_id: str, speed: str = "normal", seed: int | None = None) -> None:
    style = get_loading_style(theme_id)
    rng = random.Random(seed)
    ascii_only = not _stdout_can_encode(format_loading_bar(theme_id, 100))
    color, reset = _terminal_loading_color(theme_id)
    print(f"{color}{style.label}{reset}")
    for stage in style.stages:
        print(f"{color}[LOAD] {stage}{reset}")
        time.sleep(_delay_for_step(speed, rng))
    for percent in range(0, 101, 5):
        sys.stdout.write("\r" + color + format_loading_bar(theme_id, percent, ascii_only=ascii_only) + reset)
        sys.stdout.flush()
        time.sleep(_delay_for_step(speed, rng))
    print()
