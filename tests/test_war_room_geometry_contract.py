from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.helpers.gui_harness import build_layout_for
from ui.components.header import (
    GUI_LOGO_BOX_HEIGHT,
    HEADER_LOGO_FLEX,
    HEADER_STATUS_FLEX,
    HEADER_STATUS_METADATA_FLEX,
    HEADER_TELEMETRY_FLEX,
    THEME_HEADER_SPLITS,
    THEME_LOGO_LAYOUTS,
    theme_header_split,
    theme_logo_layout_mode,
)
from ui.components.monolith_panel import MONOLITH_CARD_COUNT
from ui.components.theme_switcher import THEME_SWITCHER_WIDTH
from ui.flet_app import (
    CENTER_COLUMN_FLEX,
    FOOTER_HEIGHT,
    LEFT_COLUMN_FLEX,
    PROPOSAL_HEIGHT,
    RIGHT_COLUMN_FLEX,
)
from ui.themes.catalog import GUI_THEME_KEYS, THEMES


VIEWPORTS = ((1920, 1080), (1536, 864), (2560, 1440))
BODY_VERTICAL_PADDING = 16
LEFT_TITLE_HEIGHT = 22
FOOTER_GAP = 4


def _monolith_cards(layout: ft.Control) -> list[ft.Control]:
    left_column = layout.content.controls[1].content.controls[0].content
    return [
        control
        for control in left_column.controls
        if isinstance(getattr(control, "data", None), dict)
        and control.data.get("role") == "monolith_card"
    ]


def test_main_layout_uses_visual_review_ratios() -> None:
    layout = build_layout_for("eva")
    left, center, right = layout.content.controls[1].content.controls

    assert [left.expand, center.expand, right.expand] == [LEFT_COLUMN_FLEX, CENTER_COLUMN_FLEX, RIGHT_COLUMN_FLEX]


def test_header_uses_approved_theme_geometry() -> None:
    for theme_key in GUI_THEME_KEYS:
        header = build_layout_for(theme_key).content.controls[0]
        logo_box, status_box = header.content.controls
        status_content = status_box.content.controls[1]
        status_metadata, telemetry = status_content.controls
        mode = theme_logo_layout_mode(THEMES[theme_key])["mode"]

        if mode == "percentage":
            expected_logo, expected_status = theme_header_split(THEMES[theme_key])
            assert logo_box.expand == expected_logo
            assert status_box.expand == expected_status
            assert logo_box.width is None
        elif mode in {"square", "supersampled_square"}:
            assert logo_box.width == GUI_LOGO_BOX_HEIGHT
            assert logo_box.height == GUI_LOGO_BOX_HEIGHT
            assert logo_box.expand is None
            assert status_box.expand is True
        elif mode in {"supersampled_rect", "supersampled_banner"}:
            assert logo_box.width is not None
            assert logo_box.height is not None
            assert logo_box.expand is None
            assert status_box.expand is True
        elif mode == "historical":
            assert logo_box.width is not None
            assert logo_box.expand is None
            assert status_box.expand is True
        assert status_metadata.expand == HEADER_STATUS_METADATA_FLEX
        assert telemetry.expand == HEADER_TELEMETRY_FLEX

    assert THEME_HEADER_SPLITS["default"] == (HEADER_LOGO_FLEX, HEADER_STATUS_FLEX)
    assert THEME_HEADER_SPLITS["arasaka"] == (34, 66)
    assert THEME_HEADER_SPLITS["janus"] == (18, 82)
    assert THEME_HEADER_SPLITS["helldivers"] == (20, 80)
    assert "eva" not in THEME_HEADER_SPLITS
    assert "wh40k" not in THEME_HEADER_SPLITS
    assert THEME_LOGO_LAYOUTS["eva"]["mode"] == "supersampled_rect"
    assert THEME_LOGO_LAYOUTS["wh40k"]["mode"] == "supersampled_rect"
    assert THEME_LOGO_LAYOUTS["military"]["mode"] == "supersampled_banner"


def test_monolith_cards_clear_footer_at_review_viewports() -> None:
    for theme_key in GUI_THEME_KEYS:
        layout = build_layout_for(theme_key)
        header = layout.content.controls[0]
        left_column = layout.content.controls[1].content.controls[0].content
        cards = _monolith_cards(layout)

        assert len(cards) == MONOLITH_CARD_COUNT
        assert all(card.expand == 1 for card in cards)

        for _width, viewport_height in VIEWPORTS:
            body_height = viewport_height - int(header.height) - FOOTER_HEIGHT - BODY_VERTICAL_PADDING
            expandable_controls = [control for control in left_column.controls if getattr(control, "expand", None)]
            total_expand = sum(int(control.expand) for control in expandable_controls)
            gaps = left_column.spacing * (len(left_column.controls) - 1)
            available_for_expand = body_height - LEFT_TITLE_HEIGHT - gaps
            card_height = available_for_expand / total_expand
            arbiter_bottom = int(header.height) + (BODY_VERTICAL_PADDING / 2) + LEFT_TITLE_HEIGHT + left_column.spacing
            arbiter_bottom += (card_height + left_column.spacing) * (MONOLITH_CARD_COUNT - 1) + card_height
            footer_top = viewport_height - FOOTER_HEIGHT

            assert card_height >= 96, f"{theme_key} card height too small at {viewport_height}px"
            assert arbiter_bottom <= footer_top - FOOTER_GAP, theme_key


def test_footer_and_proposal_controls_have_fixed_review_dimensions() -> None:
    layout = build_layout_for("janus")
    footer = layout.content.controls[2]
    footer_theme_region = footer.content.controls[0]
    footer_aux_region = footer.content.controls[2]
    switcher = footer_theme_region.content
    proposal_region = layout.content.controls[1].content.controls[1].content.controls[0]

    assert footer.height == FOOTER_HEIGHT
    assert footer_theme_region.width == THEME_SWITCHER_WIDTH
    assert switcher.width == THEME_SWITCHER_WIDTH
    assert footer_aux_region.width == 125
    assert proposal_region.height == PROPOSAL_HEIGHT
    assert proposal_region.expand is None


if __name__ == "__main__":
    test_main_layout_uses_visual_review_ratios()
    test_header_uses_approved_theme_geometry()
    test_monolith_cards_clear_footer_at_review_viewports()
    test_footer_and_proposal_controls_have_fixed_review_dimensions()
    print("test_war_room_geometry_contract PASS")
