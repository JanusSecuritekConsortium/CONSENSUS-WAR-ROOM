import importlib
import shutil

import pytest

from config.nodes import DEFAULT_NODES
from core import paths
from core.prompting import assembler
from tools import boot


def test_frozen_prompt_resources_use_bundle_not_executable_directory(monkeypatch, tmp_path):
    bundle = tmp_path / "bundle"
    profiles = bundle / "monoliths" / "profiles"
    shutil.copytree(assembler.PROFILE_DIR, profiles)
    with monkeypatch.context() as patch:
        patch.setattr(paths, "RESOURCE_ROOT", bundle)
        patch.setattr(paths, "SYSTEM_ROOT", tmp_path / "empty_install_directory")
        importlib.reload(assembler)
        try:
            for node in DEFAULT_NODES.values():
                prompt = assembler.assemble_monolith_prompt(node, "Is consensus online and ready?", {})
                assert f"canonical_id: {node.codename}" in prompt
        finally:
            patch.undo()
            importlib.reload(assembler)


def test_packaged_self_test_fails_when_profile_is_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(assembler, "PROFILE_DIR", tmp_path)
    assert boot.run_self_test() == 1
    output = capsys.readouterr().out
    assert "PROMPT SUBSYSTEM: ERROR" in output
    assert "Missing monolith profile" in output


def test_submission_file_error_does_not_claim_mock_fallback(monkeypatch):
    from tests.helpers.gui_harness import make_gui_state
    from ui import flet_app as gui

    state = make_gui_state("wh40k")
    monkeypatch.setattr(gui, "MstyRuntime", lambda config: object())
    monkeypatch.setattr(gui, "_fallback_warning", lambda *args: "")
    monkeypatch.setattr(gui, "create_proposal", lambda **kwargs: {"proposal_id": "missing-profile-test"})
    monkeypatch.setattr(gui, "build_context_packet", lambda *args: {})
    monkeypatch.setattr(gui, "build_bellator_context_packet", lambda *args: {})
    monkeypatch.setattr(gui, "build_bellator_diagnostics_payload", lambda *args: {})
    def missing(*args):
        raise FileNotFoundError("Missing monolith profile: bellator.json")
    monkeypatch.setattr(gui, "build_node_prompt", missing)
    with pytest.raises(FileNotFoundError):
        gui.submit_proposal_live_for_gui(state, "Is consensus online and ready?", skip_animations=True)
    assert "bellator.json" in state.displayed_synthesis
    assert "SUBMISSION FAILED" in state.provider_warning
    assert "MOCK FALLBACK ACTIVE" not in state.provider_warning
    assert "bellator.json" in state.timeline_events[-1]
