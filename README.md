# CONSENSUS War Room

CONSENSUS War Room is a Windows-first, local multi-agent tribunal for proposal
review. RATIONALIS, AETERNUM, and BELLATOR assess a proposal from different
perspectives; the ARBITER combines their votes into an auditable verdict.

The current release is **v8.0.0**. It includes a Flet desktop interface, CLI and
local API entry points, deterministic offline operation, Msty/Ollama-compatible
provider adapters, real-data enrichment, simulations, voice integrations, and
Windows packaging.

Author: Project contributors, CONSENSUS project.

## Status

| Area | State |
| --- | --- |
| Tribunal | Deterministic classification, quorum, confidence, review triggers, voting, and decision traces |
| Desktop UI | Flet War Room with proposal history, verdict export, diagnostics, telemetry, and six theme families |
| Providers | Msty-first local routing, Ollama-compatible options, readiness checks, and controlled mock fallback |
| Data | RSS-first cached enrichment with explicit unavailable/degraded states |
| API | Local REST decisions and analytics plus status-only WebSocket lifecycle events |
| Packaging | PyInstaller-based Windows executable and packaged self-test |
| Verification | Python 3.10 CI, active-tree compilation, and categorized regression tests |

See [the changelog](CHANGELOG.md) for release history and
[the architecture guide](docs/ARCHITECTURE.md) for module ownership.

## Quick Start

Requirements: Windows and Python 3.10 or newer.

Linux migration support (launchers, voice fallback, and setup requirements)
is documented in [the Linux migration guide](docs/LINUX_MIGRATION.md).
Native Linux desktop and voice-model validation is still required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Start the normal desktop workflow:

```powershell
.\boot.bat
```

Useful boot modes:

```powershell
.\boot.bat --safe        # diagnostics-only recovery
.\boot.bat --validate    # release validation
.\boot.bat --test-theme  # theme/layout validation
```

Run a deterministic offline tribunal:

```powershell
python consensus_war_room_genesis.py --no-boot --backend mock "Should we proceed?"
```

Run health checks and tests:

```powershell
python consensus_war_room_genesis.py --health
python tools\run_tests.py
```

For the standard pytest workflow:

```powershell
python -m pip install -e .[dev]
python -m pytest
```

## Runtime Modes

```powershell
# CLI
python consensus_war_room_genesis.py "Your proposal here"

# Desktop GUI
python consensus_war_room_genesis.py --gui

# Local API (127.0.0.1:8888 by default)
python consensus_war_room_genesis.py --api

# Provider diagnostics
python consensus_war_room_genesis.py --provider-status --verbose
python consensus_war_room_genesis.py --list-models
```

Primary API routes:

- `POST /consensus` runs a tribunal decision.
- `GET /analytics/summary` returns bounded aggregate metrics.
- `GET /analytics/summary.csv` downloads the same metrics as CSV.
- `WS /ws/tribunal` streams status-only lifecycle events.

The real-time stream excludes raw model responses and internal reasoning. Keep
the API on localhost unless it is protected by an authenticated deployment
boundary.

## Operator Features

The GUI command palette opens with `Ctrl+K`. Common shortcuts are `Ctrl+D` for
diagnostics, `Ctrl+T` to cycle themes, `Ctrl+H` for proposal history, and
`Ctrl+E` to export the latest verdict.

The active release provides:

- deterministic proposal classification and multi-agent voting;
- linked proposal, verdict, and simulation records;
- Markdown, JSON, dossier, and analytics CSV exports;
- deterministic geopolitical, economic, cyber, and security scenario scaffolds;
- cache-backed RSS intelligence with source health and freshness reporting;
- EVA/MAGI, Arasaka, Military/EXCOMM, WH40K, Helldivers, and Janus themes;
- optional AURELIUS and ARBITER voice integrations.

Generated verdicts, dossiers, screenshots, manifests, caches, and histories are
written locally and intentionally excluded from Git.

## Configuration

The runtime creates `_ARBITER/genesis_config.json` when required. Create it
explicitly with:

```powershell
python consensus_war_room_genesis.py --write-default-config
```

Set `startup_theme` to `RANDOM` or a theme such as `ARASAKA`. Optional provider,
data-source, Telegram, and integration variables are documented in
[`.env.example`](.env.example). Never commit `.env` or credentials.

Available backends include:

- `mock`: deterministic offline demos and tests;
- `ollama`: a local Ollama-compatible runtime;
- `msty-local`: Msty's local LLaMA.cpp endpoint;
- `msty-claw`: the Msty Claw bridge;
- `msty-llama-cpp`: the explicit lower-level Msty endpoint.

## Data and Simulation

The data layer normalizes and caches external context for BELLATOR and
AETERNUM. RSS is the primary source; credentialed APIs are opt-in enrichment.
Unavailable or stale sources are reported instead of replaced with invented
content.

```powershell
python tools\probe_rss_feeds.py
python tools\poll_rss_feeds.py --force
python tools\poll_rss_feeds.py --watch
```

Simulations create deterministic branch and risk scaffolds from explicit
operator assumptions. They do not autonomously forecast events or invent
intelligence.

## MstyClaw MCP

The read-only MCP server is `integrations\mcp\consensus_mcp_server.py`.
Register it in MstyClaw with the repository virtual environment:

```text
Name: CONSENSUS MCP
Command: <repo>\.venv\Scripts\python.exe
Arguments: <repo>\integrations\mcp\consensus_mcp_server.py
```

It exposes status, redacted logs, model discovery, project-tree, safe-read, and
text-search tools. It does not write files, execute commands, delete data, or
access arbitrary network targets.

## Build a Windows Executable

```powershell
.\build_exe.bat
.\dist\CONSENSUS.exe --self-test
```

The generated `build/` and `dist/` trees stay local and are not committed.

## Repository Map

| Path | Purpose |
| --- | --- |
| `core/` | Tribunal, voting, memory, proposals, simulations, telemetry, API, and CLI |
| `config/` | Runtime defaults, versions, and agent identities |
| `integrations/` | Provider, feed, market, search, and MCP adapters |
| `ui/` | Flet desktop UI, components, boot flow, and themes |
| `monoliths/` | Active tribunal profiles and registry |
| `_ARBITER/` | Runtime configuration plus ignored local cache, logs, and state |
| `assistant/` | AURELIUS operator-assistant helpers |
| `voice/` | Optional voice profiles and adapters |
| `static/` | Icons, ASCII logos, and theme assets |
| `tools/` | Boot, validation, export, data-source, and packaging utilities |
| `tests/` | Regression and integration tests |
| `docs/` | Architecture, operations, migrations, and workspace documentation |

Historical experiments, future prototypes, generated reports, runtime data,
model weights, and local workspace inventories are deliberately not tracked.
Git history remains the source for retired implementations.

## Repository Hygiene

- Keep active source and maintained documentation in Git.
- Keep generated output under ignored runtime paths such as `reports/`.
- Keep experiments and local archives outside the tracked tree.
- Store secrets in environment variables or ignored local configuration.
- Add new behavior to the owning module instead of reviving legacy monoliths.

`boot.bat` is the canonical operator entry point.
`consensus_war_room_genesis.py` remains the stable compatibility entry point for
CLI, API, and older Msty workflows.

## Optional AURELIUS Agent Runtime

An opt-in operator execution layer adds bounded tool rounds, context handling,
tool retrieval, exact host approvals, MCP clients and durable background jobs.
The existing UI, voice route, tribunal models and live briefing schedules remain
the defaults. Install the optional dependency with `python -m pip install -e ".[agent]"`
and read [AURELIUS agent operations](docs/AURELIUS_AGENT.md) before enabling it.
`python -m assistant.agent --self-test` exercises the runtime offline.
Real Odysseus can complement AURELIUS over a separate local service:
[setup and permissions](docs/AURELIUS_ODYSSEUS.md). This route uses the actual
Odysseus agent API and preserves CONSENSUS reasoning and existing briefing owners.
