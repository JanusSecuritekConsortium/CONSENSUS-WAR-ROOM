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

### Tribunal

The tribunal is CONSENSUS, not AURELIUS; these tools only relay questions and results.

- `tribunal_deliberate` puts a decision question to the tribunal and returns a ticket at once. One deliberation
  runs at a time, in its own process, because the voters share one GPU. On local 33-34B models a full
  deliberation can take an hour. Unfilled templates (two or more `[FIELD]` blanks) are refused, and so is a
  start when the largest voter model would not fit in free RAM and graphics memory (`not_started`, with the reason).
- `tribunal_verdict` reads a ticket: queued, running (with elapsed minutes), finished with the verdict and each
  vote, or failed.
- `tribunal_track_record` lists recent real decisions with their outcomes, verdicts a week old still awaiting an
  outcome, and each member's record. Read-only.
- `tribunal_record_outcome` records whether a verdict was followed and whether it turned out good, mixed or bad.
  It writes only the local outcome store.

Job records are kept in the git-ignored `_ARBITER/memory/tribunal_jobs` folder.

Before a first live deliberation on a machine, check that every voter's model loads:

```powershell
G:\CONSENSUS_SYSTEM\.venv\Scripts\python.exe -m integrations.mcp.voter_check
```

It loads RATIONALIS, AETERNUM, BELLATOR and the base model one at a time. For each it reports ready, with the
time to the first answer and the speed, or the model server's error. A llama.cpp update can refuse files converted
for an older version. It starts no deliberation, and it refuses to run while a deliberation is running.

To check the ARBITER and AURELIUS voices' files (voice models, the voice conversion Python, ffmpeg):

```powershell
G:\CONSENSUS_SYSTEM\.venv\Scripts\python.exe -m voice.voice_check
```

It makes no sound and sends nothing. It warns when a voice file is inside `archive/`, which a clean-up could
remove. The health check runs the same check; missing voice files mark it degraded, not failed. Paths in
`voice/voice_config.json` are relative to the checkout, or start with `{drive}/` for the portable SSD.

## Self-Test

```powershell
G:\CONSENSUS_SYSTEM\.venv\Scripts\python.exe G:\CONSENSUS_SYSTEM\integrations\mcp\test_consensus_mcp.py
```
