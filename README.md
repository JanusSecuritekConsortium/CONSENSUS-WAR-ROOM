# CONSENSUS War Room

CONSENSUS War Room is a local multi-agent tribunal for proposal review. Three
specialized monoliths analyze a proposal from different perspectives, then an
arbiter combines their votes into an auditable verdict.

Author: Erhardt Von Grupten Mundt, Janus Securitek Consortium.

## Project Status

The current codebase is **v8.0.0 — Theme-Native Production Boot System**,
last patched on 2026-07-19.
CONSENSUS is an actively developed, Windows-first local application with a Flet
desktop interface, CLI and API entrypoints, a deterministic offline backend,
and adapters for local Msty/Ollama-compatible inference runtimes.

| Area | Current state |
| --- | --- |
| Tribunal | Operational deterministic classification, quorum, confidence, review triggers, voting, and auditable decision traces |
| Desktop operator UI | Operational Flet War Room with proposal lifecycle, verdict export, diagnostics, telemetry, themes, and command palette |
| Provider layer | Msty-first local routing with Ollama-compatible options, explicit readiness/degraded states, model checks, and controlled mock fallback |
| Data layer | RSS-first, cache-backed enrichment is implemented; credentialed sources are opt-in and unavailable data is reported rather than invented |
| Simulations | Operator-driven deterministic scenario scaffolding is implemented; autonomous forecasting is not |
| Packaging | PyInstaller-based standalone Windows executable and packaged self-test are implemented |
| Verification | Active-source compilation, categorized regression tooling, and Python 3.10 GitHub Actions coverage are configured |

### What changed in v8.0.0

- Six production startup layouts now match the EVA/MAGI, Arasaka, Military,
  WH40K, Helldivers, and Janus interface families instead of sharing one legacy
  boot screen.
- Startup captures a fresh, privacy-safe hardware snapshot: CPU identity and
  topology, GPU/display identity when available, RAM, operating system, and
  system-drive capacity. User, network, and serial identifiers are suppressed.
- Boot rendering supports full and compact terminal layouts, theme-specific
  animation and loading geometry, balanced timing, reduced-motion rendering,
  and interactive preview controls.
- The same theme identity and provider status carry through console startup,
  Flet startup, and the main War Room handoff.

See [CHANGELOG.md](CHANGELOG.md) for the release history and
[CONSENSUS_ARCHITECTURE.md](CONSENSUS_ARCHITECTURE.md) for module ownership.

## Current System

- `RATIONALIS`: logic, consistency, and acceptance criteria
- `AETERNUM`: finance, precedent, and long-range risk
- `BELLATOR`: security, tactical exposure, and operational risk
- `ARBITER`: quorum, confidence, review triggers, and final synthesis

`AURELIUS` is an optional operator-assistant/integration layer. It is not a
tribunal voter and does not independently resolve providers or verdicts.

The active implementation lives in `core/`, `config/`, `integrations/`, `ui/`,
and `monoliths/`. Legacy experiments and prototypes are preserved separately in
`archive/` and `future_implementations/`.

## Quick Start

Use Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Normal operator startup:

```powershell
.\boot.bat
```

Normal boot runs only lightweight dependency/provider health checks, selects the
configured or random startup theme, runs BIOS/POST, and launches the GUI. It
does not run `tools\run_tests.py`, active-tree compilation, or screenshot
regression checks.

The six selectable GUI theme families are EVA/MAGI, Arasaka, Military/EXCOMM,
WH40K/Cogitator, Helldivers/Super Earth, and Janus. `NERV` remains a CLI/config
compatibility alias in the EVA/MAGI family.

Diagnostics-only recovery mode:

```powershell
.\boot.bat --safe
```

Release validation mode:

```powershell
.\boot.bat --validate
```

Developer theme/layout validation:

```powershell
.\boot.bat --test-theme
```

`boot.bat` is the canonical operator entrypoint. It validates the local
environment, checks dependencies and provider status, selects the configured or
random startup theme, runs the themed BIOS/POST sequence, and opens the GUI.
Normal operation does not require Python arguments.

### Standalone Windows Executable

Build the standalone operator executable with:

```powershell
.\build_exe.bat
```

The output is `dist\CONSENSUS.exe`. Normal operation requires no Python
arguments:

```powershell
.\dist\CONSENSUS.exe
```

Diagnostics-only recovery mode:

```powershell
.\dist\CONSENSUS.exe --safe
```

Packaged asset, voice configuration, and deterministic simulation scaffold check:

```powershell
.\dist\CONSENSUS.exe --self-test
```

The executable uses the same startup flow as `boot.bat`: dependency checks,
Msty provider validation, random or configured theme selection, BIOS/POST
output, then GUI launch.

Run an offline mock tribunal:

```powershell
python consensus_war_room_genesis.py --no-boot --backend mock "Should we document and test the next implementation?"
```

Run health checks:

```powershell
python consensus_war_room_genesis.py --health
```

Run tests:

```powershell
python tools\run_tests.py
```

`pytest` is optional for developer workflows and is not required by runtime dependencies.
If you install the development extra, you can also run:

```powershell
python -m pip install -e .[dev]
python -m pytest
```

## Runtime Modes

CLI tribunal:

```powershell
python consensus_war_room_genesis.py "Your proposal here"
```

GUI:

```powershell
python consensus_war_room_genesis.py --gui
```

The desktop GUI uses a dedicated CONSENSUS War Room tribunal icon from
`static/icons/`, separate from the individual theme ASCII logos.

API:

```powershell
python consensus_war_room_genesis.py --api
```

The API binds to `127.0.0.1:8888` by default. Its primary operational routes are:

- `POST /consensus`: run a tribunal decision.
- `GET /analytics/summary`: bounded aggregate decision metrics.
- `GET /analytics/summary.csv`: download the same summary as flat CSV rows.
- `WS /ws/tribunal`: receive `consensus_started`, `consensus_complete`, and
  `consensus_failed` lifecycle events. Clients may send `{"type":"ping"}` and
  receive a `pong` health response.

The real-time stream intentionally excludes raw model responses and internal
reasoning. Expose the API beyond localhost only behind an authenticated reverse
proxy or equivalent trusted deployment boundary.

Example CSV download:

```powershell
curl.exe -o consensus_summary.csv http://127.0.0.1:8888/analytics/summary.csv
```

Provider diagnostics:

```powershell
python consensus_war_room_genesis.py --provider-status --verbose
python consensus_war_room_genesis.py --list-models
```

## Operator Workflow

The GUI command palette opens with `Ctrl+K`. Current operator shortcuts:

- `Ctrl+D`: diagnostics drawer
- `Ctrl+T`: cycle theme
- `Ctrl+H`: proposal history
- `Ctrl+E`: export latest verdict

Proposal templates are available from the proposal panel for geopolitical,
market/finance, technical, operational-risk, and general tribunal queries.
Proposal history is stored locally as JSONL and can be resent, duplicated for
editing, or archived from the Proposal History overlay.

Export the latest verdict outside the GUI:

```powershell
python tools\export_latest_verdict.py
```

Proposal records are linked to finalized decision traces when the tribunal
returns a verdict. Linked records carry decision status, decision timestamp, and
verdict export paths. Export a combined proposal/verdict dossier:

```powershell
python tools\export_dossier.py <proposal_id>
```

During live GUI tribunal runs the Arbiter Verdict panel exposes the active
processing lifecycle: classification, dispatch, analysis, deliberation,
synthesis, terminal verdict state, and export-ready status. The GUI also shows a
bounded status-only reasoning stream and convergence meter; these are operator
state signals, not hidden chain-of-thought.

## Simulation Layer

The simulation layer is deterministic scaffolding for geopolitical, economic,
cyber, and security branch analysis. It defines scenario and branch records, a
simulation type registry, bounded probability/risk scoring helpers, and
append-only local JSONL history. It does not generate autonomous forecasts or
invented geopolitical predictions.

GUI command palette actions:

- `Create Simulation`: opens an operator input overlay and creates a deterministic scaffold linked to the current proposal context when available.
- `View Simulations`: opens simulation history and branch-tree actions.
- `Export Simulation Dossier`: exports the selected or latest scenario as Markdown and JSON.

Branch expansion requires explicit operator assumptions. The system records
deterministic branch probability/risk scaffolding only and does not generate
forecasts or invented intelligence.

## Real Data Layer

The current data-source foundation, introduced in v7.13, supplies normalized,
cache-backed external context for `BELLATOR` and `AETERNUM`. RSS is the primary
Bellator intelligence layer. APIs are enrichment only. Tribunal prompt
enrichment explicitly reports unavailable data; it never invents intelligence
when a source is disabled, unconfigured, stale, or empty.

The RSS cache is `_ARBITER/cache/data_sources/intelligence.db`. It uses SQLite
FTS5 retrieval, GUID/URL/content-hash deduplication, conditional HTTP requests,
and per-source failure backoff. The default poll interval is 20 minutes.
Bellator receives at most 12 cited items after query, taxonomy, freshness, and
deduplication filters. If refresh fails, cached items are explicitly marked
`CACHE_FALLBACK`.

Probe configured endpoints before enabling or scheduling ingestion:

```powershell
python tools\probe_rss_feeds.py
python tools\poll_rss_feeds.py --force
python tools\poll_rss_feeds.py --watch
```

`--watch` keeps the local ingestion process running at the configured interval.
Reuters and AP are quarantined until current XML endpoints are confirmed.
NATO remains quarantined while its official directory transition is resolved.
ECB and European Council feeds are discovered from their official directory
pages rather than hardcoded from assumptions.

Public GDELT remains enabled as Tier 3 enrichment. Credentialed sources stay
disabled until explicitly enabled in `config/data_sources.json` and configured
through environment variables. Ground News integration requires official API
access and does not scrape. IBKR access is read-only and rejects order
placement.

GUI command palette actions:

- `Refresh Data Sources`: background live refresh with TTL cache fallback.
- `View Source Health`: redacted adapter health and configuration status.
- `View Bellator Intel Feed`: normalized conflict/security context.
- `View Aeternum Market Feed`: normalized market/economic context.

Optional environment variables are listed in `.env.example`.

## Configuration

The default runtime config is written to `_ARBITER/genesis_config.json` when the
system first needs it. You can create it explicitly:

```powershell
python consensus_war_room_genesis.py --write-default-config
```

Set `startup_theme` to `RANDOM` for a random theme on each `boot.bat` launch, or
set it to a theme name such as `ARASAKA`.

Useful environment variables are documented in `.env.example`.

Common backend choices:

- `mock`: deterministic offline demo and tests
- `ollama`: local Ollama-compatible runtime
- `msty-local`: Msty local LLaMA.cpp endpoint
- `msty-claw`: Msty Claw bridge endpoint
- `msty-llama-cpp`: explicit Msty lower-level LLaMA.cpp endpoint

## MstyClaw MCP

CONSENSUS exposes a read-only local MCP server for MstyClaw at:

```text
integrations\mcp\consensus_mcp_server.py
```

Register it in MstyClaw as a local command, replacing `<repo>` with this
repository's absolute path:

```text
Name: CONSENSUS MCP
Command: <repo>\.venv\Scripts\python.exe
Arguments: <repo>\integrations\mcp\consensus_mcp_server.py
```

Fallback launcher:

```text
integrations\mcp\run_consensus_mcp.bat
```

The MCP server exposes read-only status, AURELIUS logs, Msty model discovery,
project tree, safe file read, and project text search tools. It does not execute
commands, write files, delete files, or access external network targets.

## Repository Map

- `core/`: tribunal logic, voting, memory, health checks, CLI
- `_ARBITER/`: local runtime configuration and ignored logs, cache, exports, and decision state
- `config/`: agent identities, node defaults, runtime config
- `integrations/`: Msty/Ollama-compatible provider adapters
- `ui/`: Flet GUI and themed terminal rendering
- `monoliths/`: active monolith profile registry
- `assistant/`: Aurelius assistant persona/runtime helpers
- `voice/`: optional operator voice adapters and ARBITER verdict announcements
- `static/`: ASCII logo and theme assets
- `tests/`: focused regression tests
- `tools/`: boot, validation, export, data-source, and packaging utilities
- `docs/`: maintenance and architecture notes
- `future_implementations/`: Riko and Flet prototype material for later work
- `archive/`: historical code snapshots and imported demos

## Wider Local Workspace

This repository sits inside a larger `G:\` workspace that includes Msty Studio,
local model folders, TARS assets, Kiwix/Msty knowledge exports, Flet prototypes,
and Obsidian notes. See:

- `docs/WORKSPACE_ECOSYSTEM.md`
- `docs/MSTY_STUDIO_CONTEXT.md`
- `scripts/workspace_inventory.ps1`

Those files document how the project relates to the wider local system without
committing installed applications, model weights, private notes, or generated
runtime data.

## Git Hygiene

The repository intentionally ignores runtime state, caches, logs, memory dumps,
exports, virtual environments, model weights, voice datasets, and audio assets.
Keep secrets in environment variables or local ignored config files.

## Notes

`main.py` and `consensus_war_room_genesis.py` are both launchers for the active
CLI. `consensus_war_room_genesis.py` remains the stable command target for older
local workflows and Msty integration notes.
