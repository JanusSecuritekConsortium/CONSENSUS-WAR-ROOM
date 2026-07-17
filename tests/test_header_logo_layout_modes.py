from __future__ import annotations

import ctypes
import hashlib
import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for, header_logo_control_for
from ui.assets.logo_normalizer import read_normalized_logo
from ui.assets.registry import THEME_GRAPHIC_ASSETS
from ui.components.header import (
    GUI_LOGO_BOX_HEIGHT,
    LOGO_FONT_FAMILY,
    MILITARY_FONT_REGISTRATION_PATH,
    MILITARY_HISTORICAL_RENDERER_COMMIT,
    header_logo_layout,
    supersampled_logo_metrics,
    theme_logo_layout_mode,
)
from ui.themes.catalog import THEMES

SQUARE_CELL_MARGIN = 6
EXPECTED_HASHES = {
    "eva": "5c10f1a59339b6a788880c4187481c0d3290abddc1dff9da80389fa8684df476",
    "wh40k": "dfe05107f652c009ef1c7a5efc6005adc82ceae42ff321870acdb67c21ec150c",
}
BOOT_HASHES = {
    "eva": "04786ec6cbfad90e20c91a4ff8e3de24ef056320734f4174add37631cf1069b8",
    "wh40k": "c15e317b7230dcff6ba757a1426aeae2266da88a23c3f24c7c2da3ba9836d8e6",
}


def _logo_source(theme_key: str) -> str:
    asset = THEME_GRAPHIC_ASSETS[theme_key]
    return asset.logo_path.read_bytes().decode("utf-8")


def _logo_hash(theme_key: str) -> str:
    return hashlib.sha256(THEME_GRAPHIC_ASSETS[theme_key].logo_path.read_bytes()).hexdigest()


def _supersampled_stack(theme_key: str) -> ft.Stack:
    layout = build_layout_for(theme_key)
    logo_box = layout.content.controls[0].content.controls[0]
    stack = logo_box.content.controls[0]
    assert isinstance(stack, ft.Stack)
    return stack


def _supersampled_canvas(theme_key: str) -> ft.Container:
    canvas = _supersampled_stack(theme_key).controls[0]
    assert isinstance(canvas, ft.Container)
    return canvas


def _assert_supersampled_rect(theme_key: str) -> None:
    layout = build_layout_for(theme_key)
    logo_box = layout.content.controls[0].content.controls[0]
    logo = _logo_source(theme_key)
    logo_layout = header_logo_layout(THEMES[theme_key])
    cell_width = int(logo_layout.logo_box_width or GUI_LOGO_BOX_HEIGHT)
    cell_height = int(logo_layout.logo_box_height or GUI_LOGO_BOX_HEIGHT)
    metrics = supersampled_logo_metrics(
        logo,
        base_font_size=int(logo_layout.logo_font_size),
        cell_width=cell_width,
        cell_height=cell_height,
        line_height_factor=logo_layout.logo_line_height,
    )

    assert theme_logo_layout_mode(THEMES[theme_key])["mode"] == "supersampled_rect"
    assert logo_box.width == cell_width
    assert logo_box.height == cell_height
    assert logo_box.data["square"] is False
    offset_x = logo_layout.logo_offset_x
    assert metrics.visible_left + offset_x >= SQUARE_CELL_MARGIN
    assert metrics.visible_right + offset_x <= cell_width - SQUARE_CELL_MARGIN
    assert metrics.visible_top >= SQUARE_CELL_MARGIN
    assert metrics.visible_bottom <= cell_height - SQUARE_CELL_MARGIN
    assert metrics.fit_scale < 1.0


def test_dense_square_logo_sources_are_current_exact_assets() -> None:
    for theme_key, expected_hash in EXPECTED_HASHES.items():
        assert _logo_hash(theme_key) == expected_hash
        assert _logo_hash(theme_key) != BOOT_HASHES[theme_key]
        if theme_key == "eva":
            assert header_logo_control_for(theme_key).value == _logo_source(theme_key)
            assert theme_logo_layout_mode(THEMES["eva"])["mode"] == "supersampled_rect"
        else:
            assert header_logo_control_for(theme_key).value == _logo_source(theme_key)
    assert not list((ROOT / "static" / "logos" / "gui").glob("*.png"))


def test_eva_uses_supersampled_rect_renderer_like_wh40k() -> None:
    layout = build_layout_for("eva")
    logo_box = layout.content.controls[0].content.controls[0]
    viewport = logo_box.content.controls[0]
    control = header_logo_control_for("eva")
    logo_layout = header_logo_layout(THEMES["eva"])
    metrics = supersampled_logo_metrics(
        _logo_source("eva"),
        base_font_size=10,
        cell_width=int(logo_layout.logo_box_width or GUI_LOGO_BOX_HEIGHT),
        cell_height=int(logo_layout.logo_box_height or GUI_LOGO_BOX_HEIGHT),
        line_height_factor=logo_layout.logo_line_height,
    )
    left, right, top, bottom = metrics.clearances

    assert theme_logo_layout_mode(THEMES["eva"])["mode"] == "supersampled_rect"
    assert logo_box.width == 185
    assert logo_box.height == 168
    assert logo_box.data["square"] is False
    assert viewport.data["role"] == "supersampled_ascii_logo_viewport"
    assert control.value == _logo_source("eva")
    assert control._Control__attrs["nowrap"][0] is True
    assert metrics.source_line_count == 56
    assert metrics.source_max_columns == 88
    assert metrics.cell_width == 185
    assert metrics.cell_height == 168
    assert metrics.base_font_size == 10
    assert 172 <= metrics.transformed_width <= 174
    assert 148 <= metrics.transformed_height <= 149
    assert left >= 6
    assert right >= 6
    assert top >= 9
    assert bottom >= 9


def test_wh40k_uses_supersampled_integer_base_font_renderer() -> None:
    _assert_supersampled_rect("wh40k")
    canvas = _supersampled_canvas("wh40k")
    control = header_logo_control_for("wh40k")
    logo_layout = header_logo_layout(THEMES["wh40k"])
    metrics = supersampled_logo_metrics(
        _logo_source("wh40k"),
        base_font_size=10,
        cell_width=int(logo_layout.logo_box_width or GUI_LOGO_BOX_HEIGHT),
        cell_height=int(logo_layout.logo_box_height or GUI_LOGO_BOX_HEIGHT),
        line_height_factor=logo_layout.logo_line_height,
    )

    assert metrics.source_line_count == 53
    assert metrics.source_max_columns == 90
    assert metrics.cell_width == 185
    assert metrics.cell_height == 168
    assert metrics.base_font_size == 10
    assert metrics.base_font_size >= 8
    assert metrics.base_font_size == int(metrics.base_font_size)
    assert metrics.base_font_size not in {2.67}
    assert header_logo_layout(THEMES["wh40k"]).logo_font_size == 10
    assert header_logo_layout(THEMES["wh40k"]).logo_visual_scale == 1.0
    assert canvas.scale.scale == metrics.fit_scale
    assert canvas.scale.scale_x is None
    assert canvas.scale.scale_y is None
    assert canvas.data["uniform_scale"] is True
    assert control._Control__attrs["nowrap"][0] is True
    assert control.overflow == ft.TextOverflow.VISIBLE
    assert control.style.overflow == ft.TextOverflow.VISIBLE


def _consolas_supports_all_characters(text: str) -> tuple[bool, list[str]]:
    chars = "".join(sorted({char for char in text if not char.isspace()}))
    gdi32 = ctypes.windll.gdi32
    user32 = ctypes.windll.user32
    hdc = user32.GetDC(None)
    font = gdi32.CreateFontW(
        0,
        0,
        0,
        0,
        400,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        LOGO_FONT_FAMILY,
    )
    old_font = gdi32.SelectObject(hdc, font)
    try:
        buffer = (ctypes.c_ushort * len(chars))()
        result = gdi32.GetGlyphIndicesW(hdc, chars, len(chars), buffer, 1)
        if result == 0xFFFFFFFF:
            return False, list(chars)
        missing = [char for char, glyph in zip(chars, buffer) if glyph == 0xFFFF]
        return not missing, missing
    finally:
        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(font)
        user32.ReleaseDC(None, hdc)


def test_military_renderer_uses_supersampled_square_text_settings() -> None:
    control = header_logo_control_for("military")
    asset_text = THEME_GRAPHIC_ASSETS["military"].logo_path.read_bytes().decode("utf-8")
    logo = read_normalized_logo(THEME_GRAPHIC_ASSETS["military"].logo_path)
    layout = header_logo_layout(THEMES["military"])

    assert MILITARY_HISTORICAL_RENDERER_COMMIT == "f7248fc"
    assert MILITARY_FONT_REGISTRATION_PATH is None
    assert theme_logo_layout_mode(THEMES["military"])["mode"] == "supersampled_square"
    assert control.value == asset_text
    assert control._Control__attrs["nowrap"][0] is True
    assert control.overflow == ft.TextOverflow.VISIBLE
    assert control.style.overflow == ft.TextOverflow.VISIBLE
    assert control.style.letter_spacing == 0
    assert control.style.word_spacing == 0
    assert control.style.height == 1.0
    assert control.font_family == LOGO_FONT_FAMILY
    assert layout.logo_font_size == 9
    assert layout.logo_box_width == 162
    assert layout.logo_box_scroll_enabled is False
    assert logo.height == 66
    assert logo.width == 100


def test_military_consolas_font_covers_all_asset_glyphs() -> None:
    asset_text = THEME_GRAPHIC_ASSETS["military"].logo_path.read_bytes().decode("utf-8")
    supported, missing = _consolas_supports_all_characters(asset_text)

    assert supported, missing


if __name__ == "__main__":
    test_dense_square_logo_sources_are_current_exact_assets()
    test_eva_uses_supersampled_rect_renderer_like_wh40k()
    test_wh40k_uses_supersampled_integer_base_font_renderer()
    test_military_renderer_uses_supersampled_square_text_settings()
    test_military_consolas_font_covers_all_asset_glyphs()
    print("test_header_logo_layout_modes PASS")
