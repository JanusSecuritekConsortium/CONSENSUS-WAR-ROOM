from __future__ import annotations

import json

from integrations.mcp.consensus_mcp_server import call_tool, handle_jsonrpc, read_project_file, redact_text


def main() -> None:
    status = call_tool("consensus_status", {})
    assert status["provider"] == "msty"
    assert status["aurelius_model"] == "qwen3:latest"

    health = call_tool("msty_health", {})
    assert "reachable" in health
    assert "latency_ms" in health

    tree = call_tool("consensus_tree", {"max_depth": 2})
    entry_parts = {
        part.strip("/\\").lower()
        for entry in tree["entries"]
        for part in entry.replace("\\", "/").split("/")
        if part.strip("/\\")
    }
    assert ".venv" not in entry_parts
    assert "archive" not in entry_parts
    assert "node_modules" not in entry_parts

    env_result = call_tool("read_project_file", {"path": ".env"})
    assert "<REDACTED>" in env_result["content"]
    assert "MSTY_API_KEY=msty" not in env_result["content"]

    try:
        read_project_file({"path": r"G:\CONSENSUS_SYSTEM_ARBITER\Bot\aurelius_bot.py"})
    except ValueError as exc:
        assert "outside CONSENSUS project root" in str(exc)
    else:
        raise AssertionError("outside-root read was not rejected")

    redacted = redact_text("AUTH_TOKEN=abc\nVISIBLE=value")
    assert "AUTH_TOKEN=<REDACTED>" in redacted
    assert "VISIBLE=value" in redacted

    response = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response and response["result"]["tools"]

    call_response = handle_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "msty_models", "arguments": {}},
        }
    )
    assert call_response and call_response["result"]["content"][0]["type"] == "text"
    json.loads(call_response["result"]["content"][0]["text"])

    print("test_consensus_mcp_server PASS")


if __name__ == "__main__":
    main()
