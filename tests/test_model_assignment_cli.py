from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.names import ARBITER, AETERNUM, BELLATOR, RATIONALIS
from config.runtime import RuntimeConfig, runtime_config_to_dict
from core.cli import main as cli_main
from integrations.msty import api as api_module


class AvailableModelsBackend:
    models = [
        "qwen3:latest",
        "deepseek-coder-33b-instruct.Q4_K_S:latest",
        "yi-34b-chat.Q4_K_S:latest",
        "cogito:latest",
    ]

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        return list(self.models)


class MistralOnlyBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        return ["mistral:latest"]


def _write_config(path: Path) -> None:
    config = RuntimeConfig(backend="msty-local")
    path.write_text(json.dumps(runtime_config_to_dict(config), indent=2), encoding="utf-8")


def _run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    original_argv = sys.argv
    try:
        sys.argv = ["main.py", *args]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                cli_main()
            except SystemExit as exc:
                if isinstance(exc.code, str):
                    stderr.write(exc.code)
                    return 1, stdout.getvalue(), stderr.getvalue()
                return int(exc.code or 0), stdout.getvalue(), stderr.getvalue()
        return 0, stdout.getvalue(), stderr.getvalue()
    finally:
        sys.argv = original_argv


def test_set_model_updates_one_monolith_config() -> None:
    original_backend = api_module.OllamaBackend
    try:
        api_module.OllamaBackend = AvailableModelsBackend
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "genesis_config.json"
            _write_config(config_path)

            code, output, _stderr = _run_cli(
                [
                    "--config",
                    str(config_path),
                    "--set-model",
                    "RATIONALIS",
                    "deepseek-coder-33b-instruct.Q4_K_S:latest",
                ]
            )
            data = json.loads(config_path.read_text(encoding="utf-8"))

        assert code == 0
        assert "Configured RATIONALIS model as: deepseek-coder-33b-instruct.Q4_K_S:latest" in output
        assert data["agent_model_overrides"][RATIONALIS] == "deepseek-coder-33b-instruct.Q4_K_S:latest"
        assert data["node_overrides"][RATIONALIS]["model"] == "deepseek-coder-33b-instruct.Q4_K_S:latest"
    finally:
        api_module.OllamaBackend = original_backend


def test_set_model_rejects_unknown_monolith() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "genesis_config.json"
        _write_config(config_path)

        code, output, stderr = _run_cli(
            ["--config", str(config_path), "--set-model", "MORPHEUS", "qwen3:latest"]
        )

    assert code == 1
    assert "Unknown monolith: MORPHEUS" in output + stderr


def test_set_model_warns_when_model_unavailable() -> None:
    original_backend = api_module.OllamaBackend
    try:
        api_module.OllamaBackend = MistralOnlyBackend
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "genesis_config.json"
            _write_config(config_path)

            code, output, _stderr = _run_cli(
                [
                    "--config",
                    str(config_path),
                    "--set-model",
                    "BELLATOR",
                    "cogito:latest",
                ]
            )

        assert code == 0
        assert "WARNING: model is not currently available from provider: cogito:latest" in output
    finally:
        api_module.OllamaBackend = original_backend


def test_show_model_config_prints_effective_models() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "genesis_config.json"
        config = RuntimeConfig(
            agent_model_overrides={
                ARBITER: "qwen3:latest",
                RATIONALIS: "deepseek-coder-33b-instruct.Q4_K_S:latest",
                AETERNUM: "yi-34b-chat.Q4_K_S:latest",
                BELLATOR: "cogito:latest",
            },
            node_overrides={
                RATIONALIS: {"model": "deepseek-coder-33b-instruct.Q4_K_S:latest"},
                AETERNUM: {"model": "yi-34b-chat.Q4_K_S:latest"},
                BELLATOR: {"model": "cogito:latest"},
            },
        )
        config_path.write_text(json.dumps(runtime_config_to_dict(config), indent=2), encoding="utf-8")

        code, output, _stderr = _run_cli(["--config", str(config_path), "--show-model-config"])

    assert code == 0
    assert "ARBITER: qwen3:latest" in output
    assert "RATIONALIS: deepseek-coder-33b-instruct.Q4_K_S:latest" in output
    assert "AETERNUM: yi-34b-chat.Q4_K_S:latest" in output
    assert "BELLATOR: cogito:latest" in output


def test_check_models_passes_when_configured_models_exist() -> None:
    original_backend = api_module.OllamaBackend
    try:
        api_module.OllamaBackend = AvailableModelsBackend
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "genesis_config.json"
            config = RuntimeConfig(
                backend="msty-local",
                agent_model_overrides={
                    ARBITER: "qwen3:latest",
                    RATIONALIS: "deepseek-coder-33b-instruct.Q4_K_S:latest",
                    AETERNUM: "yi-34b-chat.Q4_K_S:latest",
                    BELLATOR: "cogito:latest",
                },
                node_overrides={
                    RATIONALIS: {"model": "deepseek-coder-33b-instruct.Q4_K_S:latest"},
                    AETERNUM: {"model": "yi-34b-chat.Q4_K_S:latest"},
                    BELLATOR: {"model": "cogito:latest"},
                },
            )
            config_path.write_text(json.dumps(runtime_config_to_dict(config), indent=2), encoding="utf-8")

            code, output, _stderr = _run_cli(["--config", str(config_path), "--check-models"])

        assert code == 0
        assert "MISSING REQUIRED MODELS: none" in output
    finally:
        api_module.OllamaBackend = original_backend


if __name__ == "__main__":
    test_set_model_updates_one_monolith_config()
    test_set_model_rejects_unknown_monolith()
    test_set_model_warns_when_model_unavailable()
    test_show_model_config_prints_effective_models()
    test_check_models_passes_when_configured_models_exist()
    print("test_model_assignment_cli PASS")
