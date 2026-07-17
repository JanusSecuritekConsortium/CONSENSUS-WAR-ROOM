from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import boot


def _ready_dependencies() -> dict[str, object]:
    return {"missing_required": [], "required_dependencies": {}, "optional_dependencies": {}, "status": "READY"}


def test_normal_boot_does_not_run_validation_commands() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config.json"
        config.write_text(json.dumps({"startup_theme": "EVA", "backend": "mock"}), encoding="utf-8")
        original_dependencies = boot.build_dependency_report
        original_provider = boot.health_check
        original_run_command = boot._run_command
        events: list[str] = []
        try:
            boot.build_dependency_report = _ready_dependencies
            boot.health_check = lambda _config, _nodes: {"status": "ready", "backend": "mock"}
            boot._run_command = lambda _args: (_ for _ in ()).throw(AssertionError("validation command ran during normal boot"))
            code = boot.run_boot(
                config_path=config,
                render_bios=lambda **_kwargs: events.append("bios"),
                launch_gui=lambda *_args, **_kwargs: events.append("gui"),
            )
            assert code == 0
            assert events == ["bios", "gui"]
        finally:
            boot.build_dependency_report = original_dependencies
            boot.health_check = original_provider
            boot._run_command = original_run_command


def test_release_validation_runs_fast_tests_compile_and_gallery() -> None:
    original_run_command = boot._run_command
    commands: list[list[str]] = []
    try:
        boot._run_command = lambda args: commands.append(args) or 0
        assert boot.run_release_validation() == 0
    finally:
        boot._run_command = original_run_command

    joined = [" ".join(command) for command in commands]
    assert any("tools\\run_tests.py" in command and "--fast" in command for command in joined)
    assert any("tools\\compile_active_tree.py" in command for command in joined)
    assert any("tools\\export_theme_gallery.py" in command for command in joined)


def test_theme_validation_runs_only_theme_layout_scripts() -> None:
    original_run_command = boot._run_command
    commands: list[list[str]] = []
    try:
        boot._run_command = lambda args: commands.append(args) or 0
        assert boot.run_theme_validation() == 0
    finally:
        boot._run_command = original_run_command

    assert commands
    assert all("run_tests.py" not in " ".join(command) for command in commands)
    assert all("compile_active_tree.py" not in " ".join(command) for command in commands)
    assert all("export_theme_gallery.py" not in " ".join(command) for command in commands)
    assert any("test_theme_safe_ui_scaling.py" in " ".join(command) for command in commands)


if __name__ == "__main__":
    test_normal_boot_does_not_run_validation_commands()
    test_release_validation_runs_fast_tests_compile_and_gallery()
    test_theme_validation_runs_only_theme_layout_scripts()
    print("test_boot_validation_modes PASS")
