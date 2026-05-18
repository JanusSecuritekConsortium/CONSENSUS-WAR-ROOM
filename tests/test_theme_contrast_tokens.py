from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import ARBITER, TRIBUNAL_AGENT_IDS
from config.nodes import DEFAULT_NODES
from ui.components.monolith_panel import READINESS_ROW_LABELS, build_monolith_panel
from ui.themes.catalog import THEMES


def _rgb(hex_color: str) -> tuple[float, float, float]:
    color = hex_color.lstrip("#")
    return tuple(int(color[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    red, green, blue = (_linear(channel) for channel in _rgb(hex_color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(first: str, second: str) -> float:
    light, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def test_all_themes_define_contrast_text_tokens() -> None:
    for theme in THEMES.values():
        assert theme.muted_text.startswith("#")
        assert theme.secondary_text.startswith("#")
        assert theme.panel_label.startswith("#")
        assert theme.panel_value.startswith("#")


def test_arasaka_secondary_tokens_are_not_dark_on_dark() -> None:
    theme = THEMES["arasaka"]

    for token in (theme.muted_text, theme.secondary_text, theme.panel_label, theme.panel_value):
        assert token not in {theme.background_color, theme.surface_color, theme.secondary_color}
        assert _contrast_ratio(token, theme.surface_color) >= 3.0
        assert _contrast_ratio(token, theme.background_color) >= 3.0


def test_arasaka_readiness_uses_readable_panel_tokens() -> None:
    theme = THEMES["arasaka"]
    statuses = {key: "ONLINE" for key in [*TRIBUNAL_AGENT_IDS, ARBITER]}
    panel = build_monolith_panel(
        theme,
        DEFAULT_NODES,
        statuses,
        memory_status="AVAILABLE",
        provider_status="degraded",
        last_verdict="DEADLOCK",
        session_id="arasaka-contrast-session",
        lifecycle_state="IDLE",
    )
    readiness = panel.controls[-1]
    readiness_rows = readiness.content.controls[1]
    labels = [row.controls[1].value for row in readiness_rows.controls]

    assert tuple(labels) == READINESS_ROW_LABELS
    for row in readiness_rows.controls:
        label_text = row.controls[1]
        value_text = row.controls[2]
        assert label_text.color == theme.panel_label
        if label_text.value == "PROVIDER":
            assert value_text.color == theme.warning_color
        else:
            assert value_text.color == theme.panel_value


if __name__ == "__main__":
    test_all_themes_define_contrast_text_tokens()
    test_arasaka_secondary_tokens_are_not_dark_on_dark()
    test_arasaka_readiness_uses_readable_panel_tokens()
    print("test_theme_contrast_tokens PASS")
