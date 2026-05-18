from __future__ import annotations

import time
from pathlib import Path
from typing import Dict

from config.version import SYSTEM_VERSION
from core.models import Theme
from core.paths import ARBITER_DIR, SYSTEM_ROOT
from ui.animations.loading import build_loading_sample_text, render_loading_sample
from ui.themes.boot_profiles import get_boot_profile


LOGO_DIR = SYSTEM_ROOT / "static" / "logos"
THEME_PREVIEW_DIR = ARBITER_DIR / "theme_previews"


def load_logo_text(theme: Theme) -> str:
    return Path(theme.logo_path).read_text(encoding="utf-8")


def load_logo_asset(name: str) -> str:
    return (LOGO_DIR / name).read_text(encoding="utf-8")


def flet_logo_text_options(theme: Theme) -> Dict[str, object]:
    return {
        "font_family": theme.font_family,
        "selectable": False,
        "no_wrap": True,
    }


def build_global_boot_text() -> str:
    lines = [
        load_logo_asset("nerv_logo.txt"),
        f"CONSENSUS TACTICAL BIOS v{SYSTEM_VERSION} - (C) ARASAKA CORPORATION",
        "Chief Architect: Erhardt Von Grupten Mundt",
        "Quantum Computing Division / Tactical AI Systems",
        "-" * 79,
        f"WAR ROOM INIT PROTOCOL | S/N: 0xC0A57A71C | BUILD: v{SYSTEM_VERSION}",
        "Neural Processor: 4.1 GHz | Threads: 16 Active",
        "",
        "[SYS] POST: Quantum Core Check.................................OK",
        "[SYS] CPU: Consensus Neural Thread v9.12.......................OK",
        "[SYS] RAM: 65536MB ECC Quantum Memory..........................OK",
        "[SYS] GPU: NERV ARX-7 [8192 TFLOPS]............................OK",
        "[SYS] TPM: Quantum Cryptographic Module........................OK",
        "[SYS] NVMe: Hyperlane Storage x16..............................OK",
        "[SYS] NET: Secure Tunnel Port 7851.............................OK",
        "",
        "[INIT] Initializing AI Tribunal:",
        " -> RATIONALIS [Logic Engine]...................................OK",
        " -> AETERNUM [Temporal Core]....................................OK",
        " -> BELLATOR [Tactical Matrix]..................................OK",
        "",
        "[AI] Neural Networks: Calibrated...............................OK",
        "[AI] TTS Engine: GLaDOS Core....................................OK",
        "[AI] Proposal Watcher: Armed....................................OK",
        "[AI] Memory Store: Mounted......................................OK",
        "",
        "[SEC] Firewall: Hardened........................................OK",
        "[SEC] Audit Trail: Immutable....................................ACTIVE",
        "",
        "CONSENSUS SYSTEM READY",
    ]
    return "\n".join(lines) + "\n"


def build_global_loading_text(width: int = 60) -> str:
    filled = width * 4 // 5
    bar = "[" + ("#" * filled) + ("-" * (width - filled)) + "]"
    return "\n".join(
        [
            load_logo_asset("arasaka_logo.txt"),
            "INITIALIZING CONSENSUS WAR ROOM",
            bar + " 80%",
            "[LOAD] Executive clearance grid....................OK",
            "[LOAD] Counterintelligence route...................OK",
            "[LOAD] Tribunal interface..........................OK",
        ]
    ) + "\n"


def build_theme_bios_sample_text(theme: Theme) -> str:
    profile = get_boot_profile(theme.boot_profile_id)
    from ui.animations.bios_boot import generate_bios_boot_lines

    lines = [
        f"{theme.display_name.upper()} BIOS SAMPLE",
        f"PROFILE: {profile.key}",
        f"LOGO ASSET: {theme.logo_id}",
        f"PANEL: {theme.panel_style}",
        f"BORDER: {theme.border_style}",
        "-" * 72,
    ]
    lines.extend(generate_bios_boot_lines(theme.key, SYSTEM_VERSION, include_logo=False, include_loading=False))
    return "\n".join(lines) + "\n"


def render_boot_sequence(theme: Theme, speed: float = 0.08) -> None:
    for line in build_global_boot_text().splitlines():
        print(line)
        time.sleep(speed)
    print()
    print(build_global_loading_text(), end="")


def build_theme_preview_text(theme: Theme, ascii_only: bool = False) -> str:
    profile = get_boot_profile(theme.boot_profile_id)
    lines = [
        load_logo_text(theme),
        f"{theme.display_name} | canonical={theme.key}",
        "-" * 72,
        "THEME METADATA",
        f"aliases: {', '.join(theme.aliases)}",
        f"boot_profile: {theme.boot_profile_id}",
        f"boot_headline: {profile.headline}",
        f"loading_animation: {theme.loading_animation_type}",
        f"panel_style: {theme.panel_style}",
        f"border_style: {theme.border_style}",
        f"font_family: {theme.font_family}",
        f"logo: {theme.logo_id} -> {theme.logo_path}",
        "",
        "MONOLITH LABELS",
    ]
    for key, labels in theme.monolith_labels.items():
        lines.append(f"{key}: {labels['node']} | {labels['core']}")
    lines.extend(["", "INTERFACE LABELS"])
    for key, value in theme.interface_labels.items():
        lines.append(f"{key}: {value}")
    lines.extend(["", "COLORS"])
    for name, value in theme.palette.items():
        lines.append(f"{name}: {value}")
    lines.extend(["", "THEME BIOS SAMPLE", build_theme_bios_sample_text(theme)])
    lines.extend(["THEME LOADING SAMPLE", build_loading_sample_text(theme, ascii_only=ascii_only)])
    return "\n".join(lines)


def _stdout_can_encode(text: str) -> bool:
    import sys

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
    encoding = __import__("sys").stdout.encoding or "utf-8"
    return translated.encode(encoding, errors="replace").decode(encoding, errors="replace")


def render_theme_preview(theme: Theme) -> None:
    text = build_theme_preview_text(theme)
    if not _stdout_can_encode(text):
        text = build_theme_preview_text(theme, ascii_only=True)
    if not _stdout_can_encode(text):
        text = _console_safe_text(text)
    print(text)


def export_theme_preview(theme: Theme) -> Path:
    THEME_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    path = THEME_PREVIEW_DIR / f"{theme.key}_preview.txt"
    path.write_text(build_theme_preview_text(theme), encoding="utf-8")
    return path


def export_legacy_visual_reference() -> Path:
    THEME_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    path = THEME_PREVIEW_DIR / "legacy_visual_reference.txt"
    content = "\n".join(
        [
            "LEGACY VISUAL REFERENCE",
            "=" * 72,
            "NERV LOGO",
            load_logo_asset("nerv_logo.txt"),
            "ARASAKA LOGO",
            load_logo_asset("arasaka_logo.txt"),
            "JANUS LOGO",
            load_logo_asset("janus_logo.txt"),
            "CONSENSUS LOGO",
            load_logo_asset("consensus_logo.txt"),
            "LEGACY_REFERENCE_SEQUENCE",
            "GLOBAL BOOT SAMPLE",
            build_global_boot_text(),
            "GLOBAL LOADING SAMPLE",
            build_global_loading_text(),
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path
