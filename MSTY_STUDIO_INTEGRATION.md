# Msty Studio Integration for CONSENSUS War Room Genesis

## Objective

Use Msty Studio as the primary human-facing platform while CONSENSUS War Room Genesis runs locally as a tribunal service.

The recommended architecture is:

1. Msty Studio Desktop manages local models through Local AI/Ollama.
2. `consensus_war_room_genesis.py` runs as a local API.
3. `integrations/msty/runtime.py` owns per-agent runtime sessions and provider fallback.
4. Msty Studio calls the local API through a Live Context.
4. Msty Claw can use the same workspace and API for autonomous review tasks.

## Run Genesis Locally

Start the API:

```powershell
python consensus_war_room_genesis.py --api --backend msty-local --theme eva
```

Launch the local Flet War Room GUI:

```powershell
python main.py --gui --theme eva --backend msty-local
```

The GUI runs the same selected-theme BIOS boot first, then opens the Flet interface with the same active theme. If the local Msty/Ollama-compatible provider is unavailable, the GUI still opens and marks provider status as degraded; proposal submission can continue through configured mock or runtime fallback behavior.

The GUI also includes an AURELIUS Voice Loop toggle. AURELIUS is an operator assistant layer for local voice/TTS workflows; it consumes the existing runtime state and does not perform its own provider/model checks or bypass the tribunal path.

Or double-click:

```text
scripts\start_genesis_api_msty.bat
```

Default API base:

```text
http://127.0.0.1:8888
```

Health check:

```text
GET http://127.0.0.1:8888/health
```

## Msty Studio Live Context

Create a new Live Context in Msty Studio.

Use:

```text
Name: CONSENSUS War Room Tribunal
Method: POST
URL: http://127.0.0.1:8888/msty/live-context
Mode: Pull
```

The same setup is stored locally at:

```text
_ARBITER/msty_live_context_tool.json
```

Request body:

```json
{
  "query": "{query:'Proposal to submit to the tribunal'}",
  "theme": "eva",
  "backend": "msty-local",
  "sequential": false
}
```

Processing function:

```javascript
return JSON.stringify(data, null, 2)
```

Notes for the model:

```text
Use this Live Context when the user asks for a proposal review, go/no-go decision, budget/security tradeoff, risk assessment, or tribunal vote. The tool returns a verdict, confidence, individual monolith votes, review triggers, and an audit session id.
```

Optional system prompt helper:

```text
GET http://127.0.0.1:8888/msty/system-prompt
```

## Local Models

`msty-local` is an explicit alias for the local Ollama-compatible service used by Msty Studio Local AI.

Your Msty Providers screen shows this local Ollama provider:

```text
http://127.0.0.1:11964
```

Override it if needed:

```powershell
$env:MSTY_BASE_URL="http://127.0.0.1:11964"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11964"
python consensus_war_room_genesis.py --api --backend msty-local
```

Endpoint resolution order is:

```text
requested runtime backend
msty-llama-cpp at http://localhost:11454
ollama-direct at http://127.0.0.1:11434
mock fallback if enabled
```

Provider status endpoint:

```text
GET http://127.0.0.1:8888/provider/status
```

Runtime health uses degraded/offline mode when the local Msty/Ollama-compatible provider is unavailable or required models are missing. Mock fallback remains available for smoke tests and local development unless disabled.

Provider discovery now treats `http://127.0.0.1:11964` as `msty-claw`: a Msty Claw / tool orchestration bridge, not the normal model inference runtime. The default local inference runtime is `msty-llama-cpp` at `http://localhost:11454`. Ollama at `http://127.0.0.1:11434` remains the lowest-priority local provider fallback.

`--provider-diagnose --verbose` still probes the Claw service and reports whether it is offline, a tool bridge, or inference-capable. It is not selected as the model backend unless explicitly requested and compatible.

Verbose diagnostics show fallback decisions and model alias matching:

```powershell
python main.py --provider-status --backend msty-llama-cpp --verbose
python main.py --check-models --backend msty-llama-cpp --verbose
python main.py --health --verbose
```

Provider model enumeration is cached for 120 seconds by default to avoid repeated slow `/models` and `/v1/models` calls. Use `--refresh-model-cache` when you need a live refresh:

```powershell
python main.py --check-models --backend msty-llama-cpp --verbose --refresh-model-cache
python main.py --check-models --backend msty-llama-cpp --verbose
```

Verbose output reports cache hit/miss/refresh state, cache age, TTL, original enumeration latency, and current check latency. The cache is not used as health truth if the backend endpoint is offline.

CLI provider checks:

```powershell
python main.py --provider-status --backend msty-local
python main.py --provider-diagnose --backend msty-local
python main.py --list-models --backend msty-local
python main.py --check-models --backend msty-local
python main.py --set-all-models mistral:latest
python main.py --set-model ARBITER qwen3:latest
python main.py --show-model-config
```

If the configured endpoint is offline, these commands report `PROVIDER STATUS: OFFLINE`, the endpoint, `MODEL COUNT: 0`, and a short offline message instead of printing a raw connection traceback.

Fallback policy:

```text
READY: use provider models.
DEGRADED: use available provider models and mock missing monoliths when fallback is enabled.
DEGRADED_MODEL_REMAP: use_available_model_fallback is enabled and missing required models are temporarily routed to the first available model.
OFFLINE: mock all monoliths when fallback is enabled.
STRICT: fail instead of falling back.
```

Proposal prompts now include a lightweight memory context packet before they are sent to provider models. The packet is built from `_ARBITER/memory/session_memory.json`, `_ARBITER/memory/context_index.json`, and `_ARBITER/decision_history.json` using keyword/tag overlap and latest prior decisions. This is local JSON memory only; there is no vector database in v7.5.0.

Config options:

```json
{
  "mock_fallback_enabled": true,
  "strict_provider_mode": false
}
```

The Flet GUI `RECHECK PROVIDER` button refreshes endpoint health, available models, missing required models, monolith degradation state, header telemetry, and the right-side provider panel.

Active internal health also compiles the modular source boundary. Run this directly when checking local code integrity without traversing archived or legacy folders:

```powershell
python main.py --compile-active
```

The default monolith model assignments are:

```text
RATIONALIS / Logic: deepseek-coder:33b
AETERNUM / Finance: llama3.3:70b
BELLATOR / Security: mixtral:8x7b
```

Adjust these in:

```text
_ARBITER/genesis_config.json
```

Example override:

```json
{
  "backend": "msty-local",
  "theme": "eva",
  "node_overrides": {
    "LOGIC": {
      "model": "llama3.1:8b"
    },
    "FINANCE": {
      "model": "qwen2.5:14b"
    },
    "SECURITY": {
      "model": "mistral:7b"
    }
  }
}
```

## Msty Claw Implementation

Use Msty Claw as an autonomous operator, not as the tribunal itself. The AURELIUS layer in `integrations/msty/aurelius.py` can summarize system state, submit proposals to ARBITER, query memory, prepare user-facing responses, and hold future workflow integration calls. It does not cast tribunal votes unless explicitly routed into advisory mode.

Point Claw at this workspace:

```text
G:\CONSENSUS_SYSTEM
```

Give it this brief:

```text
Run CONSENSUS War Room Genesis locally. Use the API to review proposals through the three-monolith tribunal. For every task, report the final verdict, each monolith vote, files changed, tests run, risks found, and recommended next action. Do not modify legacy files unless explicitly asked.
```

Claw can fetch a machine-readable brief from:

```text
GET http://127.0.0.1:8888/msty/claw-brief
```

## Msty Bot

Create a bot in Msty Studio and use this local prompt:

```text
_ARBITER/msty_consensus_bot_prompt.md
```

Attach the CONSENSUS Live Context to that bot. The bot should call the tribunal tool for proposal review, deployment approval, budget/security decisions, or architecture risk assessment.

Recommended Claw safety mode:

```text
Extra-Safe Mode with Docker or Podman for filesystem-changing tasks.
```

For local-only review tasks, Simple Start Mode is enough if it only calls the API and reads files.

## Practical Workflow

1. Open Msty Studio Desktop.
2. Ensure Local AI models are installed and available.
3. Start Genesis API with `--backend msty-local`.
4. Add the Live Context above.
5. Ask Msty: `Use the CONSENSUS tribunal to evaluate this proposal: ...`
6. Review the verdict and audit record in `_ARBITER/decision_history.json`.

Theme preview snapshots for visual review can be exported without starting the API:

```powershell
python main.py --preview-theme NERV --export-preview
python main.py --export-legacy-visuals
```

These write to `_ARBITER/theme_previews/`.
