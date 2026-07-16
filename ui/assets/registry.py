from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from core.paths import RESOURCE_ROOT
from ui.assets.logo_normalizer import read_normalized_logo


LOGO_SAFE_MAX_WIDTH = 96
ARASAKA_SAFE_MAX_WIDTH = 130
LOGO_SAFE_MAX_HEIGHT = 10
GUI_LOGO_DIR = RESOURCE_ROOT / "static" / "logos" / "gui"
GUI_LOGO_ROOT = GUI_LOGO_DIR.resolve()
REJECTED_GUI_LOGO_HASHES = {
    "eva": "04786ec6cbfad90e20c91a4ff8e3de24ef056320734f4174add37631cf1069b8",
    "nerv": "04786ec6cbfad90e20c91a4ff8e3de24ef056320734f4174add37631cf1069b8",
    "wh40k": "c15e317b7230dcff6ba757a1426aeae2266da88a23c3f24c7c2da3ba9836d8e6",
}


@dataclass(frozen=True)
class HeaderLogoLayout:
    logo_font_size: float = 12
    logo_line_height: float = 1.0
    logo_visual_scale: float = 1.0
    logo_top_padding: int = 4
    logo_bottom_padding: int = 4
    logo_side_padding: int = 4
    logo_vertical_align: str = "center"
    logo_horizontal_align: str = "center"
    logo_box_scroll_enabled: bool = True
    logo_box_width: int | None = None
    logo_box_max_width: int | None = None
    logo_box_height: int | None = None
    header_height: int | None = None
    logo_offset_x: int = 0
    logo_offset_y: int = 0


@dataclass(frozen=True)
class HeaderLogoProfile:
    max_width: int
    max_height: int
    padding_top: int = 1
    padding_bottom: int = 1
    alignment: str = "center"
    max_width_ratio: float = 0.85
    compact: bool = False
    crop_safe: bool = False


@dataclass(frozen=True)
class WarRoomLayoutMetadata:
    header_logo_width_ratio: float = 0.35
    header_logo_height: int | None = None
    proposal_panel_min_height: int = 235
    proposal_verdict_gap: int = 12
    telemetry_panel_height: int = 192
    footer_shortcut_alignment: str = "center"
    left_panel_compaction_allowed: bool = False


@dataclass(frozen=True)
class ThemeGraphicAsset:
    theme_key: str
    logo_path: Path
    banner: str
    accent_glyphs: tuple[str, ...]
    boot_profile: str
    canonical_tokens: tuple[str, ...]
    expected_min_lines: int = 3
    expected_max_lines: int = LOGO_SAFE_MAX_HEIGHT
    expected_min_width: int = 24
    max_width: int = LOGO_SAFE_MAX_WIDTH
    header_layout: HeaderLogoLayout = HeaderLogoLayout()
    header_profile: HeaderLogoProfile | None = None
    layout_metadata: WarRoomLayoutMetadata = WarRoomLayoutMetadata()


LOGO_PROFILES: Dict[str, HeaderLogoProfile] = {
    "arasaka": HeaderLogoProfile(max_width=122, max_height=7, max_width_ratio=0.92, compact=True),
    "wh40k": HeaderLogoProfile(max_width=90, max_height=10, max_width_ratio=0.88, compact=False),
    "magi": HeaderLogoProfile(max_width=88, max_height=8, max_width_ratio=0.80, compact=False),
    "eva": HeaderLogoProfile(max_width=88, max_height=8, max_width_ratio=0.80, compact=False),
    "nerv": HeaderLogoProfile(max_width=88, max_height=8, max_width_ratio=0.80, compact=False),
    "janus": HeaderLogoProfile(max_width=72, max_height=6, max_width_ratio=0.78, compact=True),
    "helldivers": HeaderLogoProfile(max_width=88, max_height=7, max_width_ratio=0.82, compact=True),
    "military": HeaderLogoProfile(max_width=110, max_height=10, max_width_ratio=0.85, compact=True),
}


THEME_GRAPHIC_ASSETS: Dict[str, ThemeGraphicAsset] = {
    "eva": ThemeGraphicAsset(
        "eva",
        GUI_LOGO_DIR / "eva_header.txt",
        "MAGI/NERV diagnostic styling",
        ("NERV", "MAGI", "REFERENCE"),
        "eva_boot",
        ("###########################", "################################", "#######"),
        expected_min_lines=56,
        expected_max_lines=56,
        expected_min_width=80,
        max_width=88,
        header_layout=HeaderLogoLayout(
            logo_font_size=10,
            logo_line_height=0.85,
            logo_visual_scale=1.0,
            logo_top_padding=0,
            logo_bottom_padding=0,
            logo_side_padding=0,
            logo_box_width=185,
            logo_box_height=168,
            logo_box_scroll_enabled=False,
        ),
        header_profile=LOGO_PROFILES["eva"],
        layout_metadata=WarRoomLayoutMetadata(header_logo_width_ratio=0.28),
    ),
    "nerv": ThemeGraphicAsset(
        "nerv",
        GUI_LOGO_DIR / "eva_header.txt",
        "NERV diagnostic styling",
        ("NERV", "MAGI", "REFERENCE"),
        "nerv_boot",
        ("###########################", "################################", "#######"),
        expected_min_lines=56,
        expected_max_lines=56,
        expected_min_width=80,
        max_width=88,
        header_layout=HeaderLogoLayout(
            logo_font_size=10,
            logo_line_height=0.85,
            logo_visual_scale=1.0,
            logo_top_padding=0,
            logo_bottom_padding=0,
            logo_side_padding=0,
            logo_box_width=185,
            logo_box_height=168,
            logo_box_scroll_enabled=False,
        ),
        header_profile=LOGO_PROFILES["nerv"],
        layout_metadata=WarRoomLayoutMetadata(header_logo_width_ratio=0.28),
    ),
    "wh40k": ThemeGraphicAsset(
        "wh40k",
        GUI_LOGO_DIR / "wh40k_header.txt",
        "Cogitator gothic terminal styling",
        ("COGITATOR", "MACHINE SPIRIT", "OMNISSIAH"),
        "wh40k_boot",
        ("@@@@@@@@", "@@@@@@#", "#@@"),
        expected_min_lines=53,
        expected_max_lines=53,
        expected_min_width=80,
        header_layout=HeaderLogoLayout(
            logo_font_size=10,
            logo_visual_scale=1.0,
            logo_top_padding=0,
            logo_bottom_padding=0,
            logo_side_padding=0,
            logo_box_width=185,
            logo_box_height=168,
            logo_offset_x=6,
            logo_box_scroll_enabled=False,
        ),
        header_profile=LOGO_PROFILES["wh40k"],
        layout_metadata=WarRoomLayoutMetadata(
            header_logo_width_ratio=0.33,
            header_logo_height=238,
            proposal_verdict_gap=12,
            telemetry_panel_height=198,
            left_panel_compaction_allowed=True,
        ),
    ),
    "helldivers": ThemeGraphicAsset(
        "helldivers",
        GUI_LOGO_DIR / "helldivers_header.txt",
        "Command-democracy tactical styling",
        ("SUPER EARTH", "LIBERTY", "COMMAND"),
        "helldivers_boot",
        ("###########################", "####     ########    ####", "#############"),
        expected_min_lines=19,
        expected_max_lines=19,
        expected_min_width=80,
        header_layout=HeaderLogoLayout(
            logo_font_size=7,
            logo_top_padding=8,
            logo_bottom_padding=8,
            logo_side_padding=2,
            logo_box_width=450,
            logo_box_height=154,
            logo_box_scroll_enabled=False,
        ),
        header_profile=LOGO_PROFILES["helldivers"],
        layout_metadata=WarRoomLayoutMetadata(header_logo_width_ratio=0.3),
    ),
    "arasaka": ThemeGraphicAsset(
        "arasaka",
        GUI_LOGO_DIR / "arasaka_header.txt",
        "Corporate executive terminal styling",
        ("sdmNNNs", "mNNNNNNNNNNm", "ymNNNm"),
        "arasaka_boot",
        ("sdmNNNs", "mNNNNNNNNNNm", "smMMm+---"),
        expected_min_lines=7,
        expected_min_width=110,
        max_width=ARASAKA_SAFE_MAX_WIDTH,
        header_layout=HeaderLogoLayout(
            logo_font_size=8,
            logo_top_padding=4,
            logo_bottom_padding=4,
            logo_side_padding=4,
            logo_visual_scale=1.12,
            logo_box_width=640,
        ),
        header_profile=LOGO_PROFILES["arasaka"],
        layout_metadata=WarRoomLayoutMetadata(header_logo_width_ratio=0.32),
    ),
    "janus": ThemeGraphicAsset(
        "janus",
        GUI_LOGO_DIR / "janus_header.txt",
        "Dual-front security tribunal styling",
        ("JANUS", "DUAL", "TRIBUNAL"),
        "janus_boot",
        ("88888", "88b 88", "bodP"),
        expected_min_lines=4,
        expected_min_width=40,
        header_layout=HeaderLogoLayout(
            logo_font_size=12,
            logo_top_padding=22,
            logo_bottom_padding=22,
            logo_box_width=328,
            logo_offset_x=-20,
            logo_offset_y=2,
        ),
        header_profile=LOGO_PROFILES["janus"],
    ),
    "military": ThemeGraphicAsset(
        "military",
        RESOURCE_ROOT / "static" / "logos" / "consensus_logo.txt",
        "EXCOMM tactical command styling",
        ("███████╗██╗  ██╗", "CONSENSUS WAR ROOM"),
        "military_boot",
        ("███████╗██╗  ██╗", "╚══════╝╚═╝  ╚═╝", "CONSENSUS WAR ROOM"),
        expected_min_lines=10,
        expected_max_lines=10,
        expected_min_width=80,
        header_layout=HeaderLogoLayout(logo_font_size=9, logo_top_padding=14, logo_bottom_padding=14, logo_box_width=745),
    ),
}


THEME_GRAPHIC_ASSETS["military"] = ThemeGraphicAsset(
    "military",
    GUI_LOGO_DIR / "military_header.txt",
    "EXCOMM tactical command styling",
    ("EXCOMM", "WAR ROOM", "TRIBUNAL"),
    "military_boot",
    ("███████╗██╗  ██╗", "╚══════╝╚═╝  ╚═╝", "CONSENSUS WAR ROOM"),
    expected_min_lines=10,
    expected_max_lines=10,
    expected_min_width=70,
    max_width=110,
    header_layout=HeaderLogoLayout(logo_font_size=9, logo_top_padding=14, logo_bottom_padding=14, logo_box_width=745),
    header_profile=LOGO_PROFILES["military"],
)

THEME_GRAPHIC_ASSETS["military"] = ThemeGraphicAsset(
    "military",
    GUI_LOGO_DIR / "military_header.txt",
    "Military tactical command styling",
    ("×", "÷", "-"),
    "military_boot",
    ("---×÷÷×----", "×÷÷÷÷÷÷÷÷×", "------"),
    expected_min_lines=66,
    expected_max_lines=66,
    expected_min_width=100,
    max_width=100,
    header_layout=HeaderLogoLayout(
        logo_font_size=14,
        logo_top_padding=14,
        logo_bottom_padding=14,
        logo_box_width=400,
        logo_box_scroll_enabled=False,
    ),
    header_profile=LOGO_PROFILES["military"],
)


def get_theme_graphic_asset(theme_key: str) -> ThemeGraphicAsset:
    normalized = theme_key.lower()
    if normalized not in THEME_GRAPHIC_ASSETS:
        raise KeyError(f"No graphic asset registered for theme {theme_key!r}")
    return THEME_GRAPHIC_ASSETS[normalized]


def get_theme_layout_metadata(theme_key: str) -> WarRoomLayoutMetadata:
    return get_theme_graphic_asset(theme_key).layout_metadata


def validate_gui_logo_path(path: Path) -> None:
    resolved = path.resolve()
    if GUI_LOGO_ROOT not in resolved.parents:
        raise ValueError(f"GUI logo must reside beneath {GUI_LOGO_ROOT}; received {resolved}")


def validate_theme_graphic_asset(asset: ThemeGraphicAsset) -> List[str]:
    failures: List[str] = []
    try:
        validate_gui_logo_path(asset.logo_path)
    except ValueError as exc:
        failures.append(f"{asset.theme_key}: {exc}")
    if not asset.logo_path.exists():
        return failures + [f"{asset.theme_key}: missing logo asset {asset.logo_path}"]
    try:
        raw = asset.logo_path.read_bytes()
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return failures + [f"{asset.theme_key}: logo asset is not UTF-8 readable: {exc}"]
    digest = hashlib.sha256(raw).hexdigest()
    rejected_hash = REJECTED_GUI_LOGO_HASHES.get(asset.theme_key)
    if rejected_hash is not None and digest == rejected_hash:
        failures.append(f"{asset.theme_key}: GUI logo uses rejected boot asset hash {digest}")
    if text.startswith("\ufeff") or raw.startswith(b"\xef\xbb\xbf"):
        failures.append(f"{asset.theme_key}: logo asset contains UTF-8 BOM")
    logo = read_normalized_logo(asset.logo_path)
    if not logo.text.strip():
        failures.append(f"{asset.theme_key}: logo asset is empty")
    if logo.height < asset.expected_min_lines:
        failures.append(f"{asset.theme_key}: line count {logo.height} below {asset.expected_min_lines}")
    if logo.height > asset.expected_max_lines:
        failures.append(f"{asset.theme_key}: line count {logo.height} above {asset.expected_max_lines}")
    if logo.width < asset.expected_min_width:
        failures.append(f"{asset.theme_key}: max width {logo.width} below {asset.expected_min_width}")
    if logo.width > asset.max_width:
        failures.append(f"{asset.theme_key}: max width {logo.width} above {asset.max_width}")
    for token in asset.canonical_tokens:
        if token not in logo.text:
            failures.append(f"{asset.theme_key}: missing canonical token {token!r}")
    if "â" in logo.text or "�" in logo.text:
        failures.append(f"{asset.theme_key}: logo contains mojibake characters")
    return failures


def validate_graphic_registry() -> List[str]:
    failures: List[str] = []
    for asset in THEME_GRAPHIC_ASSETS.values():
        failures.extend(validate_theme_graphic_asset(asset))
    return failures
