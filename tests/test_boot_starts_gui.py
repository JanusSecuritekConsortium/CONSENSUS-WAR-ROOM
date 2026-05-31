from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import boot


def test_normal_boot_runs_bios_then_starts_gui() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config.json"
        config.write_text(json.dumps({"startup_theme": "JANUS", "backend": "mock"}), encoding="utf-8")
        original_dependencies = boot.build_dependency_report
        original_provider = boot.health_check
        events: list[str] = []
        try:
            boot.build_dependency_report = lambda: {"missing_required": [], "required_dependencies": {}, "optional_dependencies": {}, "status": "READY"}
            boot.health_check = lambda _config, _nodes: {"status": "ready", "backend": "mock"}
            code = boot.run_boot(
                config_path=config,
                render_bios=lambda **kwargs: events.append(f"bios:{kwargs['theme_id']}"),
                launch_gui=lambda theme, *_args, **_kwargs: events.append(f"gui:{theme}"),
            )
            assert code == 0
            assert events == ["bios:janus", "gui:janus"]
        finally:
            boot.build_dependency_report = original_dependencies
            boot.health_check = original_provider


if __name__ == "__main__":
    test_normal_boot_runs_bios_then_starts_gui()
    print("test_boot_starts_gui PASS")
