# CONSENSUS War Room

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="static/branding/consensus-c2-lockup-light.svg">
  <img src="static/branding/consensus-c2-lockup-dark.svg" alt="CONSENSUS corporate identity" width="395">
</picture>

The C2 mark identifies CONSENSUS in the application, documentation and internal
information. The A3 tribunal emblem is reserved for desktop, executable and
taskbar icons. See [branding assets and usage](docs/BRANDING.md).

CONSENSUS War Room is a Windows-first, local multi-agent tribunal for proposal
review. RATIONALIS, AETERNUM, and BELLATOR assess a proposal from different
perspectives; the ARBITER combines their votes into an auditable verdict.

Each voter runs on a local model by default, or online on Claude, ChatGPT or Grok through
your own subscription, or on a paid API such as DeepSeek. Giving the three voters models
from different companies gives the tribunal different reasoning styles. A failed online call
falls back to a shared backup model and then to the local model. See
[online models](docs/ONLINE_MODELS.md).

Another AI system can ask the tribunal for advice through the password-protected
[guest door](docs/GUEST_DOOR.md). Guest questions run on local models without the owner's
personal context, and nothing about them is saved to the owner's history.

Each proposal now runs three rounds. All monoliths first assess it independently;
then each critiques the complete set of initial assessments; finally each reads
all critiques and submits a revised final vote. Dissent is preserved. The ARBITER
still applies deterministic voting rules rather than generating another model
opinion. The legacy sequential option is accepted for compatibility; it does not
disable these shared rounds.

Every new tribunal turn must include a structured argument: one claim, supplied
source identities and supporting details, assumptions, the strongest genuine
objection, and evidence or mitigation that would change the decision. Critique
and revision turns must quote and address each peer's exact claim from the
latest completed round. Changed votes and cleared risk/review flags need an
explanation. Agreement and empty unresolved-disagreement lists are valid;
agents must not manufacture dissent. Citations are checked against supplied
source identities; this establishes traceability, not automatic fact checking.

Monolith votes remain APPROVE, DENY or ABSTAIN. Conditions are prerequisites;
an unresolved requirement needing human judgment uses a separate review flag
and reason. With high-risk review enabled (the default), a domain-relevant
critical risk or an explicit review request returns ESCALATE before an approval
can be issued. Evidence gaps return NO_CONSENSUS before majority or priority
approval, including gaps reported by a relevant role below the confidence
threshold. Majority denial remains DENY with review flags preserved. Explicitly
disabling high-risk review is recorded. Historical records remain readable.

The default temperatures are Rationalis 0.1, Aeternum 0.3, and Bellator 0.6.
Each node can override its temperature and maximum output tokens (900 by
default) through node overrides. These values reach the provider request.
The audit transcript records each round, actual model/backend, settings,
decision reasons, risks, conditions and failures. It is included in API results,
local history, session memory, decision traces and verdict/dossier exports.
Ollama generation requests are translated to OpenAI chat requests when the same
provider explicitly rejects the Ollama route with HTTP 404 or 405. The model and
generation settings are preserved; timeout/server failures are not replayed.

Real-provider tribunal calls use the preferred model, then any configured
`agent_model_fallbacks` for that role, then `base_model` (default
`Hermes-3-Llama-3.1-8B`), then other available real provider models. The same
monolith instructions, doctrine, mission, temperature and output limit apply
to every candidate. Missing, failed, empty or malformed candidates are skipped;
each attempt and substitution is recorded. A working model stays assigned to
that role for the rest of the deliberation. All three roles may use one model,
but still exchange distinct role assessments and critiques; the audit flags
`shared_model_roles` because this reduces model diversity.

`real_model_fallback_enabled` defaults to true. Setting it false, or explicitly
enabling `strict_provider_mode`, requires the preferred model. Fallback uses
models listed by the selected real provider and does not download new models.
If no candidate produces a valid response, the remaining rounds stop and return
NO_CONSENSUS with an incomplete-deliberation reason. Real tribunals never use
simulated replacement votes. Explicit mock mode labels its result SIMULATION
ONLY. Three rounds require nine model calls, so latency is higher than the
previous single-round flow. Running source processes need a reload; packaged
executables need a rebuild to include the changes.

The current release is listed at the top of [CHANGELOG.md](CHANGELOG.md). CONSENSUS includes a Flet desktop interface, CLI and
local API entry points, deterministic offline operation, Msty/Ollama-compatible
provider adapters, real-data enrichment, simulations, voice integrations, and
Windows packaging.

Maintained by the CONSENSUS project contributors.

The Flet desktop includes [DIRECTORATE](docs/DIRECTORATE.md): a teletype dispatch
desk with numbered decisions, public justifications, dissent, conditions and
source references. Open it from Ctrl+P or the bottom command bar; reports can be
copied or exported locally. Startup checks and movement preferences are under
Diagnostics → System Checks.

## Status

| Area | State |
| --- | --- |
| Tribunal | Deterministic classification, quorum, confidence, review triggers, voting, and decision traces |
| Desktop UI | Flet War Room with proposal history, verdict export, diagnostics, telemetry, and six theme families |
| Providers | Msty-first local routing, Ollama-compatible options, online voters (subscriptions or APIs), readiness checks, and controlled fallback |
| Data | RSS-first cached enrichment with explicit unavailable/degraded states |
| API | Local REST decisions and analytics plus status-only WebSocket lifecycle events |
| Packaging | PyInstaller-based Windows executable and packaged self-test |
| Verification | Python 3.10 CI, active-tree compilation, and categorized regression tests |

See [the changelog](CHANGELOG.md) for release history and
[the architecture guide](docs/ARCHITECTURE.md) for module ownership.

See [the folder guide](docs/FOLDER_GUIDE.md) for current source, runtime,
build, archive and executable locations.

Repeatable real-provider smoke checks and a 24-case synthetic decision benchmark
compare one monolith, independent votes and the full debate. Reports include
completion, inappropriate approvals, latency and vote-revision metrics; simulations
cannot establish real-model success. See [evaluation commands and limitations](docs/EVALUATION.md).

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

### What the repository does not include

The code and the default configuration are enough for the `mock` backend. A
real tribunal and the voices need files that are not in Git:

- **Language models.** Each agent's model is named in
  `_ARBITER/genesis_config.json` (`agent_model_overrides`). The GGUF files are
  public downloads; serve them with Msty Studio (llama.cpp) or an
  Ollama-compatible runtime. The current voters need about 18–19 GB each, so plan
  for a GPU with 24 GB or enough RAM to offload. The Mixtral file named for
  BELLATOR is an older conversion that current llama.cpp refuses; use a current
  conversion or another model. `python -m integrations.mcp.voter_check` reports
  whether each voter's model loads.
- **Voice models.** ARBITER and AURELIUS can speak through RVC voice models and
  an RVC Python environment, set in `voice/voice_config.json`. Neither is
  distributed. Without them, speech falls back to the system voice.
  `python -m voice.voice_check` lists what is missing.
- **Accounts and secrets.** Telegram, mail, calendar and data-source credentials
  go in `.env` (see [`.env.example`](.env.example)) or ignored local config.
- **Personal context.** The optional second brain is a local Obsidian vault
  (`CONSENSUS_SECOND_BRAIN`). Deliberation works without it.

For the standard pytest workflow:

```powershell
python -m pip install -e .[dev]
python -m pytest
```

Tests that start the real desktop app are skipped unless `CONSENSUS_GUI_TESTS=1`
is set (CI sets it), so a local run doesn't put windows on screen.

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
diagnostics, `Ctrl+T` to cycle themes, `Ctrl+H` for proposal history,
`Ctrl+E` to export the latest verdict, `Ctrl+M` for the BELLATOR world map, and `Ctrl+O` to choose and test each voter's online model.

The active release provides:

- deterministic proposal classification and multi-agent voting;
- voters on local models or online (Claude, ChatGPT and Grok subscriptions; Anthropic,
  OpenAI, DeepSeek and xAI APIs), with fallback to a backup model and the local model;
- an ASCII world map of BELLATOR feed events and GDELT news events, in the side panel
  and full screen;
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
