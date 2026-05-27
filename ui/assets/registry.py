from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from core.paths import SYSTEM_ROOT
from ui.assets.logo_normalizer import read_normalized_logo


LOGO_SAFE_MAX_WIDTH = 96
ARASAKA_SAFE_MAX_WIDTH = 130
LOGO_SAFE_MAX_HEIGHT = 10
GUI_LOGO_DIR = SYSTEM_ROOT / "static" / "logos" / "gui"


@dataclass(frozen=True)
class HeaderLogoLayout:
    logo_font_size: int = 12
    logo_top_padding: int = 4
    logo_bottom_padding: int = 4
    logo_side_padding: int = 4
    logo_vertical_align: str = "center"
    logo_horizontal_align: str = "center"
    logo_box_scroll_enabled: bool = True
    logo_box_width: int | None = None
    logo_box_max_width: int | None = None


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


THEME_GRAPHIC_ASSETS: Dict[str, ThemeGraphicAsset] = {
    "eva": ThemeGraphicAsset(
        "eva",
        GUI_LOGO_DIR / "eva_header.txt",
        "MAGI/NERV diagnostic styling",
        ("CASPER", "BALTHASAR", "MELCHIOR"),
        "eva_boot",
        ("MAGI", "CASPER", "BALTHASAR", "MELCHIOR", "MAGI TRIBUNAL ONLINE"),
        expected_min_lines=7,
        expected_min_width=55,
        header_layout=HeaderLogoLayout(logo_font_size=12, logo_top_padding=10, logo_bottom_padding=10, logo_box_width=565),
    ),
    "nerv": ThemeGraphicAsset(
        "nerv",
        GUI_LOGO_DIR / "eva_header.txt",
        "NERV diagnostic styling",
        ("CASPER", "BALTHASAR", "MELCHIOR"),
        "nerv_boot",
        ("MAGI", "CASPER", "BALTHASAR", "MELCHIOR", "MAGI TRIBUNAL ONLINE"),
        expected_min_lines=7,
        expected_min_width=55,
        header_layout=HeaderLogoLayout(logo_font_size=12, logo_top_padding=10, logo_bottom_padding=10, logo_box_width=565),
    ),
    "wh40k": ThemeGraphicAsset(
        "wh40k",
        GUI_LOGO_DIR / "wh40k_header.txt",
        "Cogitator gothic terminal styling",
        ("@@@@@@@@", "@@@@@@@#", "#@@"),
        "wh40k_boot",
        ("@@@@@@@@", "@@@@@@@#", "#@@"),
        expected_min_lines=50,
        expected_max_lines=60,
        expected_min_width=80,
        header_layout=HeaderLogoLayout(logo_font_size=4, logo_top_padding=6, logo_bottom_padding=6, logo_box_width=500),
    ),
    "helldivers": ThemeGraphicAsset(
        "helldivers",
        GUI_LOGO_DIR / "helldivers_header.txt",
        "Command-democracy tactical styling",
        ("SUPER EARTH", "MANAGED DEMOCRACY", "TACTICAL AUTHORIZATION"),
        "helldivers_boot",
        ("SUPER EARTH", "MANAGED DEMOCRACY", "TACTICAL AUTHORIZATION"),
        expected_min_lines=11,
        expected_max_lines=15,
        expected_min_width=52,
        header_layout=HeaderLogoLayout(logo_font_size=8, logo_top_padding=7, logo_bottom_padding=7, logo_box_width=640),
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
        header_layout=HeaderLogoLayout(logo_font_size=11, logo_top_padding=22, logo_bottom_padding=20, logo_box_width=1040),
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
        header_layout=HeaderLogoLayout(logo_font_size=12, logo_top_padding=22, logo_bottom_padding=22, logo_box_width=410),
    ),
    "military": ThemeGraphicAsset(
        "military",
        SYSTEM_ROOT / "static" / "logos" / "consensus_logo.txt",
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


def get_theme_graphic_asset(theme_key: str) -> ThemeGraphicAsset:
    normalized = theme_key.lower()
    if normalized not in THEME_GRAPHIC_ASSETS:
        raise KeyError(f"No graphic asset registered for theme {theme_key!r}")
    return THEME_GRAPHIC_ASSETS[normalized]


def validate_theme_graphic_asset(asset: ThemeGraphicAsset) -> List[str]:
    failures: List[str] = []
    if not asset.logo_path.exists():
        return [f"{asset.theme_key}: missing logo asset {asset.logo_path}"]
    try:
        raw = asset.logo_path.read_bytes()
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [f"{asset.theme_key}: logo asset is not UTF-8 readable: {exc}"]
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
