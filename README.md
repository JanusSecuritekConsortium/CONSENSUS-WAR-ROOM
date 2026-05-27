# CONSENSUS War Room

CONSENSUS War Room is a local multi-agent tribunal for proposal review. Three
specialized monoliths analyze a proposal from different perspectives, then an
arbiter combines their votes into an auditable verdict.

Author: Erhardt Von Grupten Mundt, Janus Securitek Consortium.

## Current System

- `RATIONALIS`: logic, consistency, and acceptance criteria
- `AETERNUM`: finance, precedent, and long-range risk
- `BELLATOR`: security, tactical exposure, and operational risk
- `ARBITER`: quorum, confidence, review triggers, and final synthesis

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

API:

```powershell
python consensus_war_room_genesis.py --api
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

## Configuration

The default runtime config is written to `_ARBITER/genesis_config.json` when the
system first needs it. You can create it explicitly:

```powershell
python consensus_war_room_genesis.py --write-default-config
```

Useful environment variables are documented in `.env.example`.

Common backend choices:

- `mock`: deterministic offline demo and tests
- `ollama`: local Ollama-compatible runtime
- `msty-local`: Msty local LLaMA.cpp endpoint
- `msty-claw`: Msty Claw bridge endpoint
- `msty-llama-cpp`: explicit Msty lower-level LLaMA.cpp endpoint

## Repository Map

- `core/`: tribunal logic, voting, memory, health checks, CLI
- `config/`: agent identities, node defaults, runtime config
- `integrations/`: Msty/Ollama-compatible provider adapters
- `ui/`: Flet GUI and themed terminal rendering
- `monoliths/`: active monolith profile registry
- `assistant/`: Aurelius assistant persona/runtime helpers
- `voice/`: optional voice adapter experiments
- `static/`: ASCII logo and theme assets
- `tests/`: focused regression tests
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
