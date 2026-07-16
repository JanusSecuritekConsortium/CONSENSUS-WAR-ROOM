from __future__ import annotations

import inspect
import hashlib
import subprocess
import sys
from pathlib import Path

import flet as ft
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for, header_logo_control_for
import ui.components.header as header_module
from ui.assets.registry import GUI_LOGO_ROOT, REJECTED_GUI_LOGO_HASHES, THEME_GRAPHIC_ASSETS, validate_gui_logo_path
from ui.components.header import LOGO_FONT_FAMILY, header_logo_layout, header_logo_text, theme_header_split, theme_logo_layout_mode
from ui.layout_contract import CENTER_COLUMN_FLEX, FOOTER_HEIGHT, LEFT_COLUMN_FLEX, PROPOSAL_HEIGHT, RIGHT_COLUMN_FLEX
from ui.themes.catalog import GUI_THEME_KEYS, THEMES


SELECTED_GUI_LOGO_SOURCES = {
    "eva": {
        "path": "static/logos/gui/eva_header.txt",
        "sha256": "5c10f1a59339b6a788880c4187481c0d3290abddc1dff9da80389fa8684df476",
        "dimensions": (56, 88),
        "boot_sha256": "04786ec6cbfad90e20c91a4ff8e3de24ef056320734f4174add37631cf1069b8",
    },
    "wh40k": {
        "path": "static/logos/gui/wh40k_header.txt",
        "sha256": "dfe05107f652c009ef1c7a5efc6005adc82ceae42ff321870acdb67c21ec150c",
        "dimensions": (53, 90),
        "boot_sha256": "c15e317b7230dcff6ba757a1426aeae2266da88a23c3f24c7c2da3ba9836d8e6",
    },
    "arasaka": {
        "path": "static/logos/gui/arasaka_header.txt",
        "sha256": "7b583e22f249e24051b8cf2c6c3d6adc1b79d455df6f058cf4fa05108f14d29a",
        "dimensions": (7, 113),
        "boot_sha256": "",
    },
    "helldivers": {
        "path": "static/logos/gui/helldivers_header.txt",
        "sha256": "2acff104e82c897b437dd7ffcefc89d49f00ebeb71c433b8daa4ddeac5f8a31c",
        "dimensions": (19, 88),
        "boot_sha256": "",
    },
    "janus": {
        "path": "static/logos/gui/janus_header.txt",
        "sha256": "7226d10d04fc42528f3a0a23d0b2002391f07ecf17e83dae62ccde9d4692bdba",
        "dimensions": (4, 43),
        "boot_sha256": "",
    },
    "military": {
        "path": "static/logos/gui/military_header.txt",
        "sha256": "cbbc12841faa0794c8653f6500dd00d117cfa28f77e2c66852e4ba776fd517b0",
        "dimensions": (67, 100),
        "boot_sha256": "",
    },
}


def _gui_asset_text(theme_key: str) -> str:
    return (ROOT / "static" / "logos" / "gui" / f"{theme_key}_header.txt").read_bytes().decode("utf-8")


def _git_asset_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def _current_asset_bytes(path: str) -> bytes:
    return (ROOT / path).read_bytes()


def _dimensions(data: bytes) -> tuple[int, int]:
    lines = data.decode("utf-8").splitlines()
    return len(lines), max((len(line) for line in lines), default=0)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_header_renders_exact_gui_logo_assets_without_substitution() -> None:
    for theme_key in GUI_THEME_KEYS:
        expected = _gui_asset_text(theme_key)

        assert header_logo_text(THEMES[theme_key]) == expected
        control = header_logo_control_for(theme_key)
        assert isinstance(control, ft.Text)
        assert control.value == expected
        assert control._Control__attrs["nowrap"][0] is True
        assert control.font_family == LOGO_FONT_FAMILY
        assert control.style.font_family == LOGO_FONT_FAMILY
        assert control.style.letter_spacing == 0
        assert control.style.word_spacing == 0
        assert control.style.height == header_logo_layout(THEMES[theme_key]).logo_line_height


def test_selected_gui_assets_are_canonical_current_sources() -> None:
    for theme_key, expected in SELECTED_GUI_LOGO_SOURCES.items():
        current = _current_asset_bytes(expected["path"])

        assert _sha256(current) == expected["sha256"], theme_key
        if expected["boot_sha256"]:
            assert _sha256(current) != expected["boot_sha256"], theme_key
        assert _dimensions(current) == expected["dimensions"], theme_key


def test_gui_logo_paths_are_semantically_isolated_from_boot_assets() -> None:
    for theme_key in ("eva", "nerv", "wh40k"):
        path = THEME_GRAPHIC_ASSETS[theme_key].logo_path.resolve()
        digest = _sha256(path.read_bytes())

        validate_gui_logo_path(path)
        assert path.parent == GUI_LOGO_ROOT
        assert "future_implementations" not in str(path)
        assert digest != REJECTED_GUI_LOGO_HASHES[theme_key]


def test_gui_logo_path_validator_rejects_boot_and_non_gui_locations() -> None:
    rejected_paths = [
        ROOT / "static" / "logos" / "nerv_logo.txt",
        ROOT / "static" / "logos" / "cogitator_logo.txt",
        ROOT / "future_implementations" / "flet_server_prototype" / "static" / "logos" / "nerv_logo.txt",
        ROOT / "reports" / "logo_history_candidates" / "retired_v7.13.30_eva_header.txt",
    ]

    for path in rejected_paths:
        with pytest.raises(ValueError):
            validate_gui_logo_path(path)


def test_logo_renderer_remains_text_based_without_normalization() -> None:
    source = inspect.getsource(header_module.header_logo_text) + inspect.getsource(header_module._logo_source_text)

    assert "read_normalized_logo" not in source
    assert "normalize" not in source
    assert "dedent" not in source
    assert "rstrip" not in source
    assert not list((ROOT / "static" / "logos" / "gui").glob("*.png"))


def test_historical_logo_renderer_settings_are_restored() -> None:
    expected = {
        "eva": {"font": 10, "scale": 1.0, "mode": "supersampled_rect"},
        "arasaka": {"font": 8, "split": (34, 66)},
        "wh40k": {"font": 10, "scale": 1.0, "mode": "supersampled_rect"},
        "military": {"font": 14, "mode": "supersampled_banner"},
        "janus": {"split": (18, 82)},
        "helldivers": {"split": (20, 80)},
    }

    for theme_key, settings in expected.items():
        layout = header_logo_layout(THEMES[theme_key])
        if "font" in settings:
            assert layout.logo_font_size == settings["font"]
            assert layout.logo_font_size not in {2.6, 2.60, 2.67}
        if "scale" in settings:
            assert layout.logo_visual_scale == settings["scale"]
        if "split" in settings:
            assert theme_header_split(THEMES[theme_key]) == settings["split"]
        if "mode" in settings:
            assert theme_logo_layout_mode(THEMES[theme_key])["mode"] == settings["mode"]
        assert header_logo_control_for(theme_key)._Control__attrs["nowrap"][0] is True


def test_logo_rollback_keeps_fixed_layout_contract() -> None:
    layout = build_layout_for("eva")
    body = layout.content.controls[1].content
    footer = layout.content.controls[2]
    proposal_region = body.controls[1].content.controls[0]

    assert [control.expand for control in body.controls] == [LEFT_COLUMN_FLEX, CENTER_COLUMN_FLEX, RIGHT_COLUMN_FLEX]
    assert proposal_region.height == PROPOSAL_HEIGHT
    assert footer.height == FOOTER_HEIGHT


if __name__ == "__main__":
    test_header_renders_exact_gui_logo_assets_without_substitution()
    test_selected_gui_assets_are_canonical_current_sources()
    test_gui_logo_paths_are_semantically_isolated_from_boot_assets()
    test_gui_logo_path_validator_rejects_boot_and_non_gui_locations()
    test_logo_renderer_remains_text_based_without_normalization()
    test_historical_logo_renderer_settings_are_restored()
    test_logo_rollback_keeps_fixed_layout_contract()
    print("test_logo_asset_rollback PASS")
