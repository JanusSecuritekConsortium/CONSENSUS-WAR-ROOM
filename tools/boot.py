from __future__ import annotations

import argparse
import random
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.nodes import DEFAULT_NODES, apply_node_overrides
from config.runtime import RuntimeConfig, load_runtime_config
from core.health import print_health_report, run_health_check
from core.paths import CONFIG_PATH
from integrations.msty.api import health_check
from tools.check_dependencies import build_dependency_report, print_human_report
from ui.animations.bios_boot import render_bios_boot_console
from ui.themes.catalog import get_gui_theme_options, resolve_theme_key


THEME_VALIDATION_TESTS = [
    "tests/test_theme_safe_ui_scaling.py",
    "tests/test_theme_header_rendering.py",
    "tests/test_header_telemetry_no_overlap_health_badge.py",
    "tests/test_top_header_telemetry_layout.py",
    "tests/test_status_panel_cleanup.py",
    "tests/test_submit_button_visible_all_themes.py",
    "tests/test_no_scrambled_ascii_logos.py",
    "tests/test_no_placeholder_logos.py",
    "tests/test_wh40k_logo_full_visibility.py",
    "tests/test_logo_registry.py",
]


def resolve_startup_theme(startup_theme: str | None, *, seed: int | None = None) -> str:
    configured = str(startup_theme or "RANDOM").strip()
    available = [theme.key for theme in get_gui_theme_options()]
    if configured.upper() == "RANDOM":
        return random.Random(seed).choice(available)
    resolved = resolve_theme_key(configured)
    if resolved not in available:
        raise ValueError(f"Unknown startup theme: {startup_theme}")
    return resolved


def run_boot(
    *,
    safe: bool = False,
    seed: int | None = None,
    config_path: Path = CONFIG_PATH,
    launch_gui: Callable[..., Any] | None = None,
    render_bios: Callable[..., Any] = render_bios_boot_console,
) -> int:
    dependencies = build_dependency_report()
    print_human_report(dependencies)
    if dependencies["missing_required"]:
        return 1

    config = load_runtime_config(config_path)
    theme_key = resolve_startup_theme(config.startup_theme, seed=seed)
    config.theme = theme_key
    nodes = apply_node_overrides(DEFAULT_NODES, config.node_overrides)
    provider = health_check(config, nodes)
    print(f"SELECTED THEME: {theme_key.upper()}")
    print(f"PROVIDER STATUS: {str(provider.get('status', 'unknown')).upper()}")
    print(f"PROVIDER BACKEND: {provider.get('active_backend') or provider.get('backend') or config.backend}")

    if safe:
        print("SAFE MODE: diagnostics only")
        report = run_health_check(config_path, config_override=config)
        print_health_report(report, verbose=True)
        return 0 if report["status"] != "fail" else 1

    render_bios(theme_id=theme_key, speed="random", seed=seed, provider_status=provider)
    if launch_gui is None:
        from ui.flet_app import run_flet_gui

        launch_gui = run_flet_gui
    launch_gui(theme_key, config, nodes, compact_header=True, window_mode="maximized")
    return 0


def _run_command(args: list[str]) -> int:
    completed = subprocess.run(args, cwd=ROOT)
    return int(completed.returncode)


def run_release_validation() -> int:
    commands = [
        [sys.executable, str(ROOT / "tools" / "run_tests.py"), "--fast", "--timeout", "480"],
        [sys.executable, str(ROOT / "tools" / "compile_active_tree.py")],
        [sys.executable, str(ROOT / "tools" / "export_theme_gallery.py"), "--timeout", "90"],
    ]
    for command in commands:
        print(f"VALIDATE: {' '.join(command)}")
        code = _run_command(command)
        if code != 0:
            return code
    return 0


def run_theme_validation() -> int:
    for relative in THEME_VALIDATION_TESTS:
        command = [sys.executable, str(ROOT / relative)]
        print(f"THEME VALIDATE: {' '.join(command)}")
        code = _run_command(command)
        if code != 0:
            return code
    return 0


def run_self_test() -> int:
    from core.simulation.scenarios import create_scenario
    from ui.assets.registry import validate_graphic_registry
    from voice.voice_profiles import get_voice_profile

    failures = validate_graphic_registry()
    if failures:
        print(f"ASSET SUBSYSTEM: ERROR ({'; '.join(failures)})")
        return 1
    profile = get_voice_profile("ARBITER_GLADOS")
    print(f"VOICE SUBSYSTEM: READY ({profile.name})")
    scenario = create_scenario(
        proposal_id=None,
        title="Runtime self-test",
        description="Deterministic scaffold validation only.",
        scenario_type="strategic_forecast",
        assumptions={"scope": "self-test only"},
        actors=["OPERATOR"],
        triggers=["SELF_TEST"],
        timeline_horizon="self-test",
        branch_depth=1,
        confidence_model="deterministic",
    )
    if not scenario.generated_branches:
        print("SIMULATION SUBSYSTEM: ERROR (initial branch missing)")
        return 1
    print(f"SIMULATION SUBSYSTEM: READY ({scenario.generated_branches[0].branch_id})")
    print("ASSET SUBSYSTEM: READY")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Boot CONSENSUS War Room.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--safe", action="store_true", help="Run diagnostics without starting the GUI.")
    mode.add_argument("--validate", action="store_true", help="Run release validation: fast tests, active compile, and theme screenshots.")
    mode.add_argument("--test-theme", action="store_true", help="Run targeted theme/layout validation only.")
    mode.add_argument("--self-test", action="store_true", help="Validate packaged assets, voice config, and simulation scaffold.")
    parser.add_argument("--seed", type=int, default=None, help="Optional deterministic startup theme seed.")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if args.validate:
        return run_release_validation()
    if args.test_theme:
        return run_theme_validation()
    return run_boot(safe=args.safe, seed=args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
