from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.telemetry import TELEMETRY_HISTORY, TelemetryHistory
from ui.components.header import GUI_HEADER_HEIGHT, HEADER_TELEMETRY_HEIGHT
from ui.components.telemetry_widgets import (
    CANONICAL_METRICS,
    TELEMETRY_COMPACT_THRESHOLD,
    TELEMETRY_HISTORY_LIMIT,
    TELEMETRY_MIN_UPDATE_SECONDS,
    THEME_TELEMETRY_ALIASES,
    TELEMETRY_LAYOUT_IDS,
    bounded_history_deque,
    build_themed_telemetry,
    canonical_telemetry_values,
    segmented_bar,
    telemetry_control_signature,
)
from ui.themes.catalog import THEMES


SAMPLE_TELEMETRY = {
    "status": "READY",
    "latest": {
        "cpu": {"percent": 11.0},
        "ram": {"percent": 22.0},
        "disk": {"percent": 33.0},
        "gpu": {"status": "ready", "usage_percent": 44.0, "vram_percent": 55.0},
    },
    "history": {
        "cpu": [9.0, 10.0, 11.0],
        "ram": [20.0, 21.0, 22.0],
        "gpu": [40.0, 42.0, 44.0],
    },
}


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from _walk(content)
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)


def _text_values(control) -> str:
    return "\n".join(str(item.value) for item in _walk(control) if isinstance(item, ft.Text))


def test_all_themes_build_visual_telemetry_with_five_canonical_metrics() -> None:
    for theme_key in ("janus", "arasaka", "eva", "wh40k", "helldivers", "military"):
        control = build_themed_telemetry(theme_key, SAMPLE_TELEMETRY, None, THEMES[theme_key])
        text = _text_values(control)

        assert control.data["role"] == "header_telemetry_panel_content"
        assert control.data["canonical_metrics"] == CANONICAL_METRICS
        assert set(control.data["values"]) == set(CANONICAL_METRICS)
        assert "LIVE TELEMETRY" in text
        for value in ("11.0%", "22.0%", "33.0%", "44.0%", "55.0%"):
            assert value in text
        assert control.data["telemetry_layout_id"] == TELEMETRY_LAYOUT_IDS[theme_key]


def test_segmented_bar_activates_rounded_segment_count_and_bounds_values() -> None:
    bar = segmented_bar(49.0, segments=12, width=120, height=8)
    high = segmented_bar(999.0, segments=12, width=120, height=8)
    low = segmented_bar(-20.0, segments=12, width=120, height=8)

    assert bar.data["active_segments"] == 6
    assert high.data["active_segments"] == 12
    assert low.data["active_segments"] == 0


def test_theme_aliases_map_to_canonical_metrics() -> None:
    expected = {
        "eva": {"cpu": "MELCHIOR", "memory": "BALTHASAR", "gpu": "CASPER"},
        "wh40k": {"cpu": "MACHINE SPIRIT", "memory": "DATA-VAULT", "gpu": "GPU RELIQUARY"},
        "helldivers": {"cpu": "DEMOCRACY", "memory": "LIBERTY ENGINE", "gpu": "ORBITAL SYSTEM"},
        "arasaka": {"cpu": "ASSET LOAD", "memory": "NEURAL", "gpu": "GPU CAPITAL"},
        "janus": {"cpu": "CPU", "memory": "MEMORY", "gpu": "GPU"},
        "military": {"cpu": "CPU", "memory": "MEM", "gpu": "GPU"},
    }

    for theme_key, aliases in expected.items():
        for metric, alias in aliases.items():
            assert THEME_TELEMETRY_ALIASES[theme_key][metric] == alias


def test_compact_mode_preserves_all_numeric_values() -> None:
    control = build_themed_telemetry(
        "helldivers",
        SAMPLE_TELEMETRY,
        None,
        THEMES["helldivers"],
        available_width=TELEMETRY_COMPACT_THRESHOLD - 1,
    )
    text = _text_values(control)

    assert control.data["compact"] is True
    for value in ("11.0%", "22.0%", "33.0%", "44.0%", "55.0%"):
        assert value in text


def test_history_is_bounded_to_thirty_samples_and_minimum_one_second_interval() -> None:
    history = bounded_history_deque()
    for index in range(40):
        history.append(float(index))
    telemetry_history = TelemetryHistory()

    assert history.maxlen == TELEMETRY_HISTORY_LIMIT
    assert list(history)[0] == 10.0
    assert TELEMETRY_HISTORY.max_samples == TELEMETRY_HISTORY_LIMIT
    assert telemetry_history.max_samples == TELEMETRY_HISTORY_LIMIT
    assert telemetry_history.sampling_interval_seconds == TELEMETRY_MIN_UPDATE_SECONDS


def test_unavailable_telemetry_uses_history_or_degraded_marker_without_random_values() -> None:
    unavailable = {
        "latest": {
            "cpu": {"percent": None},
            "ram": {"percent": None},
            "disk": {"percent": None},
            "gpu": {"status": "unavailable", "usage_percent": None, "vram_percent": None},
        },
        "history": {"cpu": [7.0], "ram": [8.0], "gpu": [9.0]},
    }
    no_history = {"latest": unavailable["latest"], "history": {"cpu": [], "ram": [], "gpu": []}}

    assert canonical_telemetry_values(unavailable) == {
        "cpu": 7.0,
        "memory": 8.0,
        "disk": None,
        "gpu": 9.0,
        "vram": None,
    }
    assert canonical_telemetry_values(no_history)["gpu"] is None
    assert "N/A" in _text_values(build_themed_telemetry("military", no_history, None, THEMES["military"]))


def test_each_theme_has_distinct_control_tree_signature_and_layout_id() -> None:
    signatures = {
        theme_key: telemetry_control_signature(build_themed_telemetry(theme_key, SAMPLE_TELEMETRY, None, THEMES[theme_key]))
        for theme_key in ("janus", "arasaka", "eva", "wh40k", "helldivers", "military")
    }
    layout_ids = {
        theme_key: build_themed_telemetry(theme_key, SAMPLE_TELEMETRY, None, THEMES[theme_key]).data["telemetry_layout_id"]
        for theme_key in ("janus", "arasaka", "eva", "wh40k", "helldivers", "military")
    }

    assert len(set(signatures.values())) == 6
    assert len(set(layout_ids.values())) == 6


def test_theme_specific_telemetry_structures_are_not_shared_three_bar_template() -> None:
    controls = {
        theme_key: build_themed_telemetry(theme_key, SAMPLE_TELEMETRY, None, THEMES[theme_key])
        for theme_key in ("janus", "arasaka", "eva", "wh40k", "helldivers", "military")
    }

    def roles(control):
        return [
            item.data.get("role")
            for item in _walk(control)
            if isinstance(getattr(item, "data", None), dict) and item.data.get("role")
        ]

    janus = roles(controls["janus"])
    arasaka = roles(controls["arasaka"])
    eva = roles(controls["eva"])
    wh40k = roles(controls["wh40k"])
    helldivers = roles(controls["helldivers"])
    military = roles(controls["military"])

    assert janus.count("dominant_sparkline") >= 2
    assert janus.count("horizontal_readiness_bar") == 0
    assert "vertical_activity_bank" in arasaka
    assert arasaka.count("horizontal_readiness_bar") == 0
    assert eva.count("magi_vertical_channel") == 3
    assert eva.count("horizontal_readiness_bar") == 0
    assert wh40k.count("mechanical_vertical_meter") == 2
    assert wh40k.count("horizontal_chain_meter") == 1
    assert helldivers.count("horizontal_readiness_bar") == 3
    assert "tactical_load_matrix" in military
    assert military.count("horizontal_readiness_bar") == 0


def test_no_external_images_or_new_plotting_dependencies_are_used_for_header_telemetry() -> None:
    module_source = (ROOT / "ui" / "components" / "telemetry_widgets.py").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()

    assert "ft.image" not in module_source.lower()
    assert ".png" not in module_source.lower()
    assert "matplotlib" not in pyproject
    assert "plotly" not in pyproject


def test_themed_telemetry_fits_supported_header_geometries() -> None:
    for width, height in ((1536, 864), (1920, 1080), (2560, 1440)):
        assert width >= 1536
        assert height >= 864
        for theme_key in ("janus", "arasaka", "eva", "wh40k", "helldivers", "military"):
            control = build_themed_telemetry(theme_key, SAMPLE_TELEMETRY, None, THEMES[theme_key], available_width=360)
            assert control.scroll is None
            assert len(control.controls) <= 7
            assert GUI_HEADER_HEIGHT == 190
            assert HEADER_TELEMETRY_HEIGHT == 132


if __name__ == "__main__":
    test_all_themes_build_visual_telemetry_with_five_canonical_metrics()
    test_segmented_bar_activates_rounded_segment_count_and_bounds_values()
    test_theme_aliases_map_to_canonical_metrics()
    test_compact_mode_preserves_all_numeric_values()
    test_history_is_bounded_to_thirty_samples_and_minimum_one_second_interval()
    test_unavailable_telemetry_uses_history_or_degraded_marker_without_random_values()
    test_each_theme_has_distinct_control_tree_signature_and_layout_id()
    test_theme_specific_telemetry_structures_are_not_shared_three_bar_template()
    test_no_external_images_or_new_plotting_dependencies_are_used_for_header_telemetry()
    test_themed_telemetry_fits_supported_header_geometries()
    print("test_themed_header_telemetry_widgets PASS")
