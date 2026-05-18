from __future__ import annotations

import contextlib
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.cli import main as cli_main
from core.llm import backends
from integrations.msty import api as api_module


class OfflineBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        if backends.requests is not None:
            raise backends.requests.ConnectionError("test provider refused connection")
        raise RuntimeError("test provider refused connection")


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
                return int(exc.code or 0), stdout.getvalue(), stderr.getvalue()
        return 0, stdout.getvalue(), stderr.getvalue()
    finally:
        sys.argv = original_argv


def _with_offline_backend(args: list[str]) -> tuple[int, str, str]:
    original_backend = api_module.OllamaBackend
    original_cache = api_module.MODEL_CACHE_PATH
    try:
        api_module.OllamaBackend = OfflineBackend
        with tempfile.TemporaryDirectory() as tmpdir:
            api_module.MODEL_CACHE_PATH = Path(tmpdir) / "provider_model_cache.json"
            return _run_cli(
                [
                    *args,
                    "--backend",
                    "msty-llama-cpp",
                    "--msty-llama-cpp-base-url",
                    "http://localhost:11454",
                ]
            )
    finally:
        api_module.OllamaBackend = original_backend
        api_module.MODEL_CACHE_PATH = original_cache


def _assert_offline_clean(output: str, stderr: str) -> None:
    combined = output + stderr

    assert "Traceback" not in combined
    assert "requests.ConnectionError" not in combined
    assert "PROVIDER STATUS: OFFLINE" in output
    assert "ENDPOINT: http://localhost:11454" in output
    assert "MODEL COUNT: 0" in output
    assert "No models available because provider is offline." in output


def test_list_models_offline_does_not_crash() -> None:
    code, output, stderr = _with_offline_backend(["--list-models"])

    assert code == 0
    _assert_offline_clean(output, stderr)


def test_provider_status_offline_does_not_crash() -> None:
    code, output, stderr = _with_offline_backend(["--provider-status"])

    assert code == 0
    _assert_offline_clean(output, stderr)


def test_check_models_offline_does_not_crash() -> None:
    code, output, stderr = _with_offline_backend(["--check-models"])

    assert code == 0
    _assert_offline_clean(output, stderr)
    assert "MISSING REQUIRED MODELS:" in output


if __name__ == "__main__":
    test_list_models_offline_does_not_crash()
    test_provider_status_offline_does_not_crash()
    test_check_models_offline_does_not_crash()
    print("test_provider_cli_offline PASS")
