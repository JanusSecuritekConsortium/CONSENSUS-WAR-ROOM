from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
from ui.animations.bios_boot import generate_bios_boot_lines
from ui.components.status_panel import build_status_panel
from ui.themes.catalog import THEMES


READY_PROVIDER = {
    "status": "ready",
    "active_backend": "msty-local",
    "backend": "msty-local",
    "base_url": "http://127.0.0.1:11964",
    "model_count": 9,
    "missing_required_models": {},
    "mock_fallback_enabled": True,
}


def _flatten_text(control) -> list[str]:
    values: list[str] = []
    if hasattr(control, "value") and isinstance(control.value, str):
        values.append(control.value)
    if hasattr(control, "content") and control.content is not None:
        values.extend(_flatten_text(control.content))
    if hasattr(control, "controls"):
        for child in control.controls:
            values.extend(_flatten_text(child))
    return values


def _boot_lines(theme_key: str = "ARASAKA") -> list[str]:
    return generate_bios_boot_lines(
        theme_key,
        SYSTEM_VERSION,
        include_logo=False,
        include_loading=False,
        provider_status=READY_PROVIDER,
    )


def _boot_lines_with_logo(theme_key: str = "ARASAKA") -> list[str]:
    return generate_bios_boot_lines(
        theme_key,
        SYSTEM_VERSION,
        include_logo=True,
        include_loading=False,
        center_logo=True,
        provider_status=READY_PROVIDER,
    )


def _post_block(lines: list[str]) -> list[str]:
    start = next(index for index, line in enumerate(lines) if line.strip() == "POST:")
    end = next(index for index, line in enumerate(lines[start + 1 :], start + 1) if line == "")
    return lines[start:end]


def test_bios_post_does_not_include_provider_endpoint_details() -> None:
    text = "\n".join(_boot_lines())

    assert "http://127.0.0.1:11964" not in text
    assert "msty-local @ http" not in text
    assert "models=9" not in text


def test_ready_provider_line_is_compact_and_theme_specific() -> None:
    expected = {
        "ARASAKA": "[OK] Corporate Runtime",
        "EVA": "[OK] MAGI Runtime",
        "NERV": "[OK] MAGI Runtime",
        "WH40K": "[OK] Cogitator Runtime",
        "HELLDIVERS": "[OK] Democracy Runtime",
        "JANUS": "[OK] Mirror Runtime",
        "MILITARY": "[OK] Command Runtime",
    }
    for theme_key, line in expected.items():
        text = "\n".join(_boot_lines(theme_key))
        assert line in text


def test_post_block_is_centered_consistently() -> None:
    block = _post_block(_boot_lines("ARASAKA"))
    leading_widths = [len(line) - len(line.lstrip(" ")) for line in block]

    assert len(set(leading_widths)) == 1
    assert leading_widths[0] > 0


def test_logo_block_has_two_blank_lines_before_bios_header() -> None:
    for theme_key, theme in THEMES.items():
        lines = "\n".join(_boot_lines_with_logo(theme_key)).splitlines()
        logo_line_count = len(Path(theme.logo_path).read_text(encoding="utf-8").rstrip("\n").splitlines())

        assert lines[logo_line_count] == "", theme_key
        assert lines[logo_line_count + 1] == "", theme_key
        assert "BIOS" in lines[logo_line_count + 2], theme_key


def test_provider_details_remain_available_in_gui_provider_panel() -> None:
    panel = build_status_panel(
        THEMES["arasaka"],
        {"status": "ready", "provider": READY_PROVIDER},
        "AVAILABLE",
    )
    text = "\n".join(_flatten_text(panel))

    assert "BACKEND: msty-local" in text
    assert "ENDPOINT: http://127.0.0.1:11964" in text
    assert "MODELS: 9" in text


if __name__ == "__main__":
    test_bios_post_does_not_include_provider_endpoint_details()
    test_ready_provider_line_is_compact_and_theme_specific()
    test_post_block_is_centered_consistently()
    test_logo_block_has_two_blank_lines_before_bios_header()
    test_provider_details_remain_available_in_gui_provider_panel()
    print("test_bios_post_formatting PASS")
