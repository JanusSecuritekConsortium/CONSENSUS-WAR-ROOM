# CONSENSUS MCP

Read-only local MCP server for MstyClaw access to CONSENSUS and AURELIUS status.

## MstyClaw Registration

Name:

```text
CONSENSUS MCP
```

Transport:

```text
Local command
```

Command:

```text
G:\CONSENSUS_SYSTEM\.venv\Scripts\python.exe
```

Arguments:

```text
G:\CONSENSUS_SYSTEM\integrations\mcp\consensus_mcp_server.py
```

Fallback launcher:

```text
G:\CONSENSUS_SYSTEM\integrations\mcp\run_consensus_mcp.bat
```

The server intentionally exposes read-only tools only. It does not execute arbitrary commands, write files, delete files, or access the network except for the local Msty endpoint at `localhost:11964`.

## Diagnostics

The stdio server writes JSONL diagnostics to:

```text
G:\CONSENSUS_SYSTEM\logs\consensus_mcp.log
```

Set `CONSENSUS_MCP_LOG` to override the path. The log records process startup, MCP `initialize`, `tools/list`, `resources/list`, `prompts/list`, and `tools/call` start/end/error events. It never writes diagnostics to stdout because stdout is reserved for JSON-RPC.

## Tools

- `consensus_status`
- `aurelius_status`
- `aurelius_recent_logs`
- `msty_models`
- `msty_health`
- `consensus_tree`
- `read_project_file`
- `search_project_text`

## Self-Test

```powershell
G:\CONSENSUS_SYSTEM\.venv\Scripts\python.exe G:\CONSENSUS_SYSTEM\integrations\mcp\test_consensus_mcp.py
```
