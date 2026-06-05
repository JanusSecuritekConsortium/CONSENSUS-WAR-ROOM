from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integrations.mcp.consensus_mcp_server import (  # noqa: E402
    PROJECT_ROOT as SERVER_ROOT,
    call_tool,
    handle_jsonrpc,
    read_project_file,
    redact_text,
)


def assert_true(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    status = call_tool("consensus_status", {})
    assert_true(status["project_root"] == str(SERVER_ROOT), "consensus_status project root mismatch")

    logs = call_tool("aurelius_recent_logs", {"lines": 5})
    assert_true("exists" in logs and "lines" in logs, "aurelius_recent_logs returned malformed response")

    health = call_tool("msty_health", {})
    assert_true("reachable" in health and "latency_ms" in health, "msty_health returned malformed response")

    models = call_tool("msty_models", {})
    assert_true("model_ids" in models and "count" in models, "msty_models returned malformed response")

    tree = call_tool("consensus_tree", {"max_depth": 2})
    entry_parts = {
        part.strip("/\\").lower()
        for entry in tree["entries"]
        for part in entry.replace("\\", "/").split("/")
        if part.strip("/\\")
    }
    for excluded in [".venv", "__pycache__", "archive", "dist", "build", "node_modules"]:
        assert_true(excluded not in entry_parts, f"consensus_tree leaked excluded folder: {excluded}")

    env_text = redact_text("MSTY_API_KEY=abc\nNORMAL=value\nBOT_TOKEN=secret")
    assert_true("MSTY_API_KEY=<REDACTED>" in env_text, ".env KEY redaction failed")
    assert_true("BOT_TOKEN=<REDACTED>" in env_text, ".env TOKEN redaction failed")
    assert_true("NORMAL=value" in env_text, "non-secret value was incorrectly redacted")

    env_result = call_tool("read_project_file", {"path": ".env"})
    assert_true("<REDACTED>" in env_result["content"], "read_project_file did not redact .env content")

    try:
        read_project_file({"path": r"G:\CONSENSUS_SYSTEM_ARBITER\Bot\aurelius_bot.py"})
    except ValueError as exc:
        assert_true("outside CONSENSUS project root" in str(exc), "unexpected path rejection error")
    else:
        raise AssertionError("read_project_file allowed path traversal/outside-root access")

    search = call_tool("search_project_text", {"query": "SYSTEM_VERSION", "path": "config"})
    assert_true(search["matches"], "search_project_text did not find SYSTEM_VERSION")

    listed = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert_true(bool(listed and listed["result"]["tools"]), "tools/list returned no tools")

    called = handle_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "consensus_status", "arguments": {}},
        }
    )
    assert_true(bool(called and called.get("result")), "tools/call failed")
    json.loads(called["result"]["content"][0]["text"])

    print("CONSENSUS MCP self-test PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
