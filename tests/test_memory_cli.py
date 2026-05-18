from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.cli import main as cli_main


def _run_cli(args: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    original_argv = sys.argv
    try:
        sys.argv = ["main.py", *args]
        with contextlib.redirect_stdout(stdout):
            try:
                cli_main()
            except SystemExit as exc:
                return int(exc.code or 0) if isinstance(exc.code, int) else 1, stdout.getvalue()
        return 0, stdout.getvalue()
    finally:
        sys.argv = original_argv


def test_memory_status_cli_prints_paths() -> None:
    code, output = _run_cli(["--memory-status"])

    assert code == 0
    assert "SESSION MEMORY:" in output
    assert "CONTEXT INDEX PATH:" in output


def test_session_summary_cli_prints_summary() -> None:
    code, output = _run_cli(["--session-summary"])

    assert code == 0
    assert "SESSION MEMORY: ACTIVE" in output


def test_search_decisions_cli_works_offline() -> None:
    code, output = _run_cli(["--search-decisions", "memory"])

    assert code == 0
    assert "SEARCH RESULTS:" in output


if __name__ == "__main__":
    test_memory_status_cli_prints_paths()
    test_session_summary_cli_prints_summary()
    test_search_decisions_cli_works_offline()
    print("test_memory_cli PASS")
