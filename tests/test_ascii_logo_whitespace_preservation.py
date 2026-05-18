from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui.animations.bios_boot as bios_boot
import ui.animations.boot as boot
from config.version import SYSTEM_VERSION
from core.models import Theme
from ui.animations.bios_boot import generate_bios_boot_lines
from ui.themes.catalog import THEMES


READY_PROVIDER = {
    "status": "ready",
    "active_backend": "msty-local",
    "base_url": "http://127.0.0.1:11964",
    "model_count": 4,
    "missing_required_models": {},
    "mock_fallback_enabled": True,
}


LOGO_FILES = [
    "nerv_logo.txt",
    "janus_logo.txt",
    "cogitator_logo.txt",
    "helldivers_logo.txt",
    "consensus_logo.txt",
    "arasaka_logo.txt",
]


def _logo_path(name: str) -> Path:
    return ROOT / "static" / "logos" / name


def test_arasaka_asset_retains_leading_whitespace() -> None:
    text = _logo_path("arasaka_logo.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    visual_lines = [line for line in lines if line.strip()]

    assert visual_lines[0].startswith(" " * 40)
    assert visual_lines[1].startswith(" " * 40)
    assert visual_lines[2].startswith(" " * 40)


def test_all_ascii_logo_assets_keep_multiline_indentation() -> None:
    for name in LOGO_FILES:
        text = _logo_path(name).read_text(encoding="utf-8")
        lines = text.splitlines()
        visual_lines = [line for line in lines if line.strip()]

        assert len(visual_lines) >= 5, name
        assert any(line.startswith(" ") for line in visual_lines), name


def test_bios_logo_centering_preserves_original_lines() -> None:
    original = _logo_path("arasaka_logo.txt").read_text(encoding="utf-8").rstrip("\n")
    centered = bios_boot._center_block(original, width=140)
    expected_pad = " " * ((140 - max(len(line) for line in original.splitlines())) // 2)

    for raw_line, centered_line in zip(original.splitlines(), centered.splitlines()):
        assert centered_line == expected_pad + raw_line


def test_boot_demo_arasaka_contains_centered_original_logo_lines() -> None:
    raw_logo = _logo_path("arasaka_logo.txt").read_text(encoding="utf-8").rstrip("\n")
    boot_lines = generate_bios_boot_lines(
        "ARASAKA",
        SYSTEM_VERSION,
        center_logo=True,
        provider_status=READY_PROVIDER,
    )
    boot_text = "\n".join(boot_lines)
    raw_width = max(len(line) for line in raw_logo.splitlines())
    expected_pad = " " * ((100 - raw_width) // 2)

    for raw_line in raw_logo.splitlines()[:10]:
        assert expected_pad + raw_line in boot_text

    header_line = next(line for line in boot_lines if "ARASAKA EXECUTIVE SECURITY BIOS" in line)
    assert header_line.startswith(" ")


def test_arasaka_wordmark_keeps_block_relative_position() -> None:
    raw_logo = _logo_path("arasaka_logo.txt").read_text(encoding="utf-8").rstrip("\n")
    centered = bios_boot._center_block(raw_logo, width=160)
    raw_lines = raw_logo.splitlines()
    centered_lines = centered.splitlines()
    expected_pad = " " * ((160 - max(len(line) for line in raw_lines)) // 2)

    top_emblem_line = raw_lines[0]
    wordmark_line = next(line for line in raw_lines if ".sdmNNNs-" in line)
    centered_top = centered_lines[raw_lines.index(top_emblem_line)]
    centered_wordmark = centered_lines[raw_lines.index(wordmark_line)]

    assert centered_top == expected_pad + top_emblem_line
    assert centered_wordmark == expected_pad + wordmark_line
    assert centered_wordmark.index(".sdmNNNs-") - centered_top.index(".--:////:--.") == (
        wordmark_line.index(".sdmNNNs-") - top_emblem_line.index(".--:////:--.")
    )


def test_logo_loaders_do_not_strip_asset_content() -> None:
    loader_sources = [
        inspect.getsource(bios_boot._logo_text),
        inspect.getsource(bios_boot._theme_logo_text),
        inspect.getsource(boot.load_logo_text),
        inspect.getsource(boot.load_logo_asset),
        inspect.getsource(Theme.logo.fget),
    ]
    forbidden = ("strip(", "lstrip(", "dedent(")

    for source in loader_sources:
        for token in forbidden:
            assert token not in source


def test_theme_logo_text_matches_asset_exactly_except_optional_eof_newline() -> None:
    for theme_key, theme in THEMES.items():
        expected = Path(theme.logo_path).read_text(encoding="utf-8").rstrip("\n")
        loaded = bios_boot._theme_logo_text(theme_key).rstrip("\n")

        assert loaded == expected, theme_key


if __name__ == "__main__":
    test_arasaka_asset_retains_leading_whitespace()
    test_all_ascii_logo_assets_keep_multiline_indentation()
    test_bios_logo_centering_preserves_original_lines()
    test_boot_demo_arasaka_contains_centered_original_logo_lines()
    test_arasaka_wordmark_keeps_block_relative_position()
    test_logo_loaders_do_not_strip_asset_content()
    test_theme_logo_text_matches_asset_exactly_except_optional_eof_newline()
    print("test_ascii_logo_whitespace_preservation PASS")
