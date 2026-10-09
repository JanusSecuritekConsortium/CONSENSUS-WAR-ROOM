import json
import pytest
from tools import boot
from ui.themes.catalog import get_gui_theme_options


@pytest.mark.parametrize("theme", [theme.key for theme in get_gui_theme_options()])
def test_default_launcher_animates_before_gui_without_prechecking_provider(monkeypatch, tmp_path, theme):
    from tools import eva_boot_dummy
    from ui.animations import bios_boot
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"startup_theme": theme, "backend": "mock"}))
    monkeypatch.setattr(boot, "build_dependency_report", lambda: {"missing_required": []})
    monkeypatch.setattr(boot, "print_human_report", lambda report: None)
    monkeypatch.setattr(boot, "health_check", lambda *a: pytest.fail("Provider check before GUI"))
    events = []
    def animated(theme_key, **kwargs):
        assert not kwargs["reduced_motion"]
        assert kwargs["interactive"]
        assert kwargs["speed"] in {"fast", "normal", "slow"}
        assert kwargs["provider_status"]["status"] == "unknown"
        events.append(("animation", theme_key))
    monkeypatch.setattr(eva_boot_dummy, "render_theme_dummy", animated)
    monkeypatch.setattr(bios_boot, "await_user_interaction", lambda: events.append(("handoff", theme)))
    def gui(theme_key, *args, **kwargs):
        assert kwargs["compact_header"] and kwargs["window_mode"] == "maximized"
        events.append(("gui", theme_key))
    assert boot.run_boot(config_path=path, launch_gui=gui, seed=17) == 0
    assert events == [("animation", theme), ("handoff", theme), ("gui", theme)]


def test_invalid_config_reaches_recovery_without_waiting_for_animation(monkeypatch, tmp_path):
    path = tmp_path / "config.json"
    path.write_text("[]")
    monkeypatch.setattr(boot, "build_dependency_report", lambda: {"missing_required": []})
    monkeypatch.setattr(boot, "print_human_report", lambda report: None)
    monkeypatch.setattr(boot, "render_bios_boot_console", lambda **kwargs: pytest.fail("Animation blocks recovery"))
    received = []
    assert boot.run_boot(config_path=path, launch_gui=lambda *a, **kw: received.append(kw)) == 0
    assert received[0]["startup_config_error"]
