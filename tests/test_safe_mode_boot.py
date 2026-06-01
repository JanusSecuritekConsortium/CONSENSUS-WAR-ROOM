from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import boot


def test_safe_mode_runs_diagnostics_without_gui_or_bios() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config.json"
        config.write_text(json.dumps({"startup_theme": "ARASAKA", "backend": "mock"}), encoding="utf-8")
        original_dependencies = boot.build_dependency_report
        original_provider = boot.health_check
        original_health = boot.run_health_check
        original_print_health = boot.print_health_report
        launched: list[str] = []
        bios: list[str] = []
        try:
            boot.build_dependency_report = lambda: {"missing_required": [], "required_dependencies": {}, "optional_dependencies": {}, "status": "READY"}
            boot.health_check = lambda _config, _nodes: {"status": "ready", "backend": "mock"}
            boot.run_health_check = lambda *_args, **_kwargs: {"status": "pass", "checks": {}}
            boot.print_health_report = lambda *_args, **_kwargs: None
            code = boot.run_boot(
                safe=True,
                config_path=config,
                launch_gui=lambda *_args, **_kwargs: launched.append("gui"),
                render_bios=lambda **_kwargs: bios.append("bios"),
            )
            assert code == 0
            assert launched == []
            assert bios == []
        finally:
            boot.build_dependency_report = original_dependencies
            boot.health_check = original_provider
            boot.run_health_check = original_health
            boot.print_health_report = original_print_health


if __name__ == "__main__":
    test_safe_mode_runs_diagnostics_without_gui_or_bios()
    print("test_safe_mode_boot PASS")
