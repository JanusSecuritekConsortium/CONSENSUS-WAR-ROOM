from __future__ import annotations

import argparse
import random
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Boot CONSENSUS War Room.")
    parser.add_argument("--safe", action="store_true", help="Run diagnostics without starting the GUI.")
    parser.add_argument("--seed", type=int, default=None, help="Optional deterministic startup theme seed.")
    args = parser.parse_args()
    return run_boot(safe=args.safe, seed=args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
