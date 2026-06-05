# CONSENSUS Project Status and Evolution Report

Generated: 2026-06-03

Workspace path inspected: `G:\CONSENSUS_SYSTEM`

Purpose: upload this report into a ChatGPT Project so the project context understands the current state, architecture, evolution, and next priorities of CONSENSUS.

## 1. Executive Summary

CONSENSUS War Room is a local Python-based multi-agent tribunal for proposal review and auditable decision synthesis. The system takes an operator proposal, dispatches it to three specialized monoliths, collects structured votes, and lets the ARBITER produce a final verdict with confidence, quorum state, review triggers, trace artifacts, and exportable reports.

The current project version is `7.13.2`, named "AURELIUS Telegram Cleanup". The latest release moved Telegram assistant operation from the deprecated ANIMA bootstrap to the clean AURELIUS bot path, using Msty-only provider routing and removing direct IBKR startup coupling.

Current runtime status is healthy:

- `python consensus_war_room_genesis.py --health` returned `HEALTH: PASS`.
- Provider status is `READY`.
- Active backend is `msty-llama-cpp`.
- Active endpoint is `http://localhost:11454`.
- Model count detected: 10.
- Required model aliases are currently satisfied.
- Fast verification passed: 205 tests passed, 0 failed.

Current git status:

- Branch: `codex/deterministic-arbiter-consensus`.
- Branch is ahead of origin by 1 commit.
- Two active local runtime/launcher edits exist in `_ARBITER/Bot/`.
- The verification run generated/updated report and verdict artifacts under `reports/`.

Important caveat: automated screenshot export is not currently treated as the release gate. The verification manifest reports `MANUAL_REVIEW_REQUIRED` for screenshots, meaning visual review still depends on operator screenshots or manual review.

## 2. Current Product Identity

Project name: `CONSENSUS War Room`

Package name: `consensus-war-room`

Current version: `7.13.2`

Description from package metadata: local multi-agent tribunal for proposal review and auditable consensus decisions.

Author metadata: Erhardt Von Grupten Mundt.

Organization URL metadata: `https://github.com/JanusSecuritekConsortium`

Primary operator concept:

- `RATIONALIS`: logic, formal consistency, feasibility, hidden assumptions, acceptance criteria.
- `AETERNUM`: finance, market impact, precedent, opportunity cost, long-range risk.
- `BELLATOR`: security, operational exposure, geopolitics, tactical and cyber risk.
- `ARBITER`: quorum, confidence, synthesis, terminal verdict, review triggers.

The project is not just a chatbot interface. It is a local decision system with structured roles, repeatable voting rules, persistent traces, proposal history, exports, data-source enrichment, simulation scaffolds, diagnostics, and GUI operator workflows.

## 3. Current Repository Layout

Active code and ownership:

- `core/`: tribunal logic, voting, memory, telemetry, proposal lifecycle, exports, simulation, data sources, runtime snapshots.
- `config/`: agent identities, node defaults, runtime config, names, version, data-source config.
- `integrations/`: Msty, Ollama, Msty Claw hooks, RSS, GDELT, ACLED, Factal, Ground News, IBKR, search, and other feed adapters.
- `ui/`: Flet desktop GUI, components, themes, boot animation, rendering, runtime GUI state.
- `monoliths/`: active monolith profile registry.
- `assistant/`: AURELIUS local assistant runtime and persona helpers.
- `voice/`: optional voice adapter experiments and insertion points.
- `static/`: theme assets, ASCII logos, GUI header marks, icons.
- `tests/`: focused regression and integration tests.
- `docs/`: maintenance, workspace ecosystem, Msty context, ARBITER decision spec, Telegram migration notes.
- `tools/`: verification, export, dependency, RSS probe/poll, visual review, and packaging helpers.
- `reports/`: generated verification manifests, proposal history, verdict exports, dossiers, visual review outputs.
- `archive/`: historical code snapshots and legacy implementations.
- `future_implementations/`: preserved prototype or planned material.
- `_ARBITER/`: runtime state, decision history, cache, voice assets, logs, Telegram bot entrypoint, generated previews.

The active implementation intentionally lives in the modular folders above. Legacy/prototype material is preserved rather than deleted, but it is excluded from active package discovery and active compile boundaries.

## 4. Runtime Entry Points

Canonical operator startup:

```powershell
.\boot.bat
```

Diagnostics-only safe mode:

```powershell
.\boot.bat --safe
```

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

Offline mock tribunal:

```powershell
python consensus_war_room_genesis.py --no-boot --backend mock "Should we document and test the next implementation?"
```

Health:

```powershell
python consensus_war_room_genesis.py --health
```

Provider diagnostics:

```powershell
python consensus_war_room_genesis.py --provider-status --verbose
python consensus_war_room_genesis.py --list-models
```

Standalone executable build:

```powershell
.\build_exe.bat
```

Standalone executable run:

```powershell
.\dist\CONSENSUS.exe
```

Executable self-test:

```powershell
.\dist\CONSENSUS.exe --self-test
```

## 5. Current Verification State

Commands run during this report:

```powershell
.\.venv\Scripts\python.exe tools\run_tests.py --fast
.\.venv\Scripts\python.exe consensus_war_room_genesis.py --health
.\.venv\Scripts\python.exe consensus_war_room_genesis.py --provider-status --verbose
```

Fast test result:

- Total test files run: 205.
- Passed: 205.
- Failed: 0.
- Duration: about 389 seconds.
- Manifest: `G:\CONSENSUS_SYSTEM\reports\verification_v7.13.2.json`.

Slow-test warning:

- `tests\test_health_badge.py` exceeded the 30 second slow threshold at about 49.15 seconds.
- This is a performance concern, not a correctness failure.

Health check result:

- `HEALTH: PASS`.
- Passing checks included config load, theme catalog load, required folders, active source compile, memory store read/write, voting parser, Msty API import, Msty runtime health, and monolith registry.

Provider check result:

- Provider status: `READY`.
- Requested backend: `msty-llama-cpp`.
- Requested endpoint: `http://localhost:11454`.
- Fallback activated: no.
- Resolved backend: `msty-llama-cpp`.
- Model count: 10.
- Missing required models: none.
- Model cache: miss during this run.
- Provider/model enumeration latency: about 29.1 seconds.

Model alias matches currently detected:

- `AETERNUM`: configured `yi-34b-chat.Q4_K_S:latest` matched provider model `TheBloke/Yi-34B-Chat-GGUF/yi-34b-chat.Q4_K_S.gguf`.
- `RATIONALIS`: configured `deepseek-coder-33b-instruct.Q4_K_S:latest` matched provider model `TheBloke/deepseek-coder-33B-instruct-GGUF/deepseek-coder-33b-instruct.Q4_K_S.gguf`.

Screenshot status:

- The verification manifest marks screenshot status as `MANUAL_REVIEW_REQUIRED`.
- Automated screenshot export is not currently a hard release gate for this pass.

## 6. Current Git and Workspace State

Current branch:

```text
codex/deterministic-arbiter-consensus
```

Remote relation:

```text
ahead of origin/codex/deterministic-arbiter-consensus by 1 commit
```

Latest commit:

```text
2c51f3b Release v7.13.2 AURELIUS Telegram cleanup
```

Most recent release commits:

- `7.13.2`: AURELIUS Telegram cleanup.
- `7.13.1`: RSS intelligence backbone.
- `7.13.0`: real data layer foundation.
- `7.12.1`: standalone executable.
- `7.12.0`: simulation workflow.
- `7.11.13`: ARBITER verdict voice dispatch.
- `7.11.12`: telemetry relocation and diagnostics freeze fix.
- `7.11.11`: WAR ROOM layout refinement.
- `7.11.10`: editable install packaging fix.
- `7.11.9`: Flet desktop runtime dependency fix.

Local modified active runtime files:

- `_ARBITER/Bot/aurelius_launcher.bat`
- `_ARBITER/Bot/ecosystem.config.js`

These two files now point AURELIUS Telegram launch to the repository virtual environment Python:

- Launcher uses `"%~dp0..\..\.venv\Scripts\python.exe" aurelius_bot.py`.
- PM2 ecosystem config uses `G:\CONSENSUS_SYSTEM\.venv\Scripts\python.exe`.

Generated artifacts from the report verification run:

- `reports/verification_v7.13.2.json` was updated.
- Several new `reports/verdicts/latest_verdict_*.json` and `.md` files were generated by tests.

These generated files are runtime/report artifacts. They should be reviewed before committing, ignored if treated as disposable runtime output, or cleaned with explicit operator approval.

## 7. Core Decision Flow

The active tribunal flow is:

```text
operator proposal
-> memory context packet
-> provider context check
-> VotingOrchestrator
-> per-monolith runtime-isolated agent sessions
-> structured votes
-> ConsensusEngine
-> TribunalResult
-> decision history and trace logs
-> session memory update
-> optional ARBITER voice announcement
-> GUI/API/CLI/export surfaces
```

Important implementation files:

- `core/tribunal.py`: high-level orchestration, session ID, memory context, votes, result recording, voice announcement.
- `core/voting/orchestrator.py`: dispatches proposals to monolith runtimes and parses votes.
- `core/voting/engine.py`: deterministic consensus calculation.
- `core/voting/rules.py`: quorum, confidence thresholds, taxonomy, domain mapping, tie-break priorities.
- `core/models.py`: shared dataclasses and enums for votes, verdicts, themes, nodes, and tribunal results.
- `core/history.py`: result serialization and legacy history migration.
- `core/logging.py`: JSONL runtime event and decision trace logging.
- `core/memory/`: session memory, retrieval, and context packet building.

Consensus defaults:

- Minimum confidence: `0.6`.
- Quorum: `2`.
- Majority: `2`.
- Evidence threshold: `0.4`.
- Classification confidence threshold: `0.6`.
- Tie-break priority: `BELLATOR`, then `RATIONALIS`, then `AETERNUM`.

Current terminal result branches include:

- `majority`.
- `classification_failure`.
- `classification_failure_critical_risk`.
- `confidence_threshold_no_quorum`.
- `confidence_threshold_final`.
- `tie_break_caution`.
- `tie_break_no_consensus`.
- `tie_break_priority`.
- `tie_break_all_abstain`.

The current verdict vocabulary includes modern values such as `APPROVE`, `DENY`, `ABSTAIN`, `NO_CONSENSUS`, `CAUTION`, and `ESCALATE`, while preserving legacy compatibility values for older history records.

## 8. Provider and Model Runtime

Primary current provider path:

- `msty-llama-cpp` at `http://localhost:11454`.

Msty Claw distinction:

- `msty-claw` at `http://127.0.0.1:11964` is classified as a Msty Claw/tool orchestration bridge.
- It is not selected as the normal model inference backend unless explicitly requested and inference-compatible.

Fallback behavior:

- `ollama-direct` is lower priority fallback.
- Mock fallback exists and is enabled unless strict mode disables it.
- Diagnostics preserve requested and resolved backend metadata so fallback is visible.

Provider cache behavior:

- Provider model enumeration is cached under `_ARBITER/provider_model_cache.json`.
- Default TTL is 120 seconds.
- Cache requires a live reachability check and cannot make an offline backend look ready.

Readiness behavior:

- Readiness retry is enabled.
- Default attempts: 3.
- Default delay: 2 seconds.
- Current readiness result during inspection: `NOT_NEEDED`.

Important environment variables:

- `MSTY_BASE_URL=http://127.0.0.1:11964`
- `MSTY_LLAMA_CPP_BASE_URL=http://localhost:11454`
- `AURELIUS_MSTY_BASE_URL=http://localhost:11454`
- `AURELIUS_PROVIDER=msty`
- `AURELIUS_PROVIDER_FALLBACK_ENABLED=false`
- `CONSENSUS_MODEL_CACHE_TTL=120`
- `CONSENSUS_READINESS_RETRY_ATTEMPTS=3`
- `CONSENSUS_READINESS_RETRY_DELAY_SECONDS=2.0`

## 9. GUI and Operator Experience

The GUI is a Flet desktop War Room interface. It is a command and visualization surface, not a replacement backend. It delegates proposal submission to the same tribunal path used by CLI/API.

Canonical GUI structure:

- Header with compact selected-theme logo, version, active mode, theme, provider state, memory state, and session ID.
- Main dashboard row with 20/60/20 left/center/right proportions.
- Left side with monolith readiness/status.
- Center with proposal input and ARBITER verdict panel.
- Right side with logs, diagnostics, feed/status context, and related panels.
- Footer with compact operator controls and shortcut guidance.

Operator shortcuts:

- `Ctrl+K`: command palette.
- `Ctrl+D`: diagnostics drawer.
- `Ctrl+T`: cycle theme.
- `Ctrl+H`: proposal history.
- `Ctrl+E`: export latest verdict.

Theme families:

- MILITARY / CONSENSUS War Room.
- EVA / NERV / MAGI.
- ARASAKA.
- JANUS.
- WH40K / Cogitator.
- HELLDIVERS / Super Earth.

Theme system notes:

- Full boot logos live under `static/logos/`.
- Dedicated GUI header marks live under `static/logos/gui/`.
- Boot/BIOS and GUI header assets are intentionally separate.
- Theme selection does not change backend provider state.
- Theme boot output is selected-theme scoped and should not leak boot material from other themes.

GUI lifecycle signals:

- `IDLE`.
- `PROPOSAL RECEIVED`.
- `MONOLITHS DELIBERATING`.
- `VOTES RECEIVED`.
- `ARBITER SYNTHESIZING`.
- `VERDICT ISSUED`.
- `ERROR / DEGRADED`.

The GUI exposes a bounded status-only reasoning stream and convergence meter. These are operator state signals and must not be treated as hidden chain-of-thought.

## 10. Proposal History, Verdicts, and Dossiers

Proposal records are stored locally as JSONL and can be resent, duplicated for editing, archived, or linked to final decision traces.

Important export tooling:

```powershell
python tools\export_latest_verdict.py
python tools\export_dossier.py <proposal_id>
```

Output types:

- Verdict Markdown.
- Verdict JSON.
- Combined proposal/verdict dossier Markdown.
- Combined proposal/verdict dossier JSON.

Recent generated report paths:

- `reports/proposal_history.jsonl`
- `reports/verdicts/latest_verdict_*.md`
- `reports/verdicts/latest_verdict_*.json`
- `reports/dossiers/`

Decision traces and memory:

- `core/history.py` records tribunal results.
- `core/logging.py` writes decision trace data.
- `core/memory/session.py` persists session records.
- `core/memory/retrieval.py` retrieves prior decision context.

## 11. Real Data Layer

The real data layer is active as a cache-backed external context foundation for `BELLATOR` and `AETERNUM`.

Current state:

- RSS is the primary Bellator intelligence backbone.
- APIs are enrichment only.
- Credentialed sources are disabled by default.
- Ground News integration requires official API access and does not scrape.
- IBKR is read-only and rejects order placement.
- Tribunal prompt enrichment explicitly reports unavailable data instead of inventing intelligence.

RSS cache:

- Path: `_ARBITER/cache/data_sources/intelligence.db`.
- Backend: SQLite with FTS5 retrieval.
- Deduplication: GUID, canonical URL, and stable content hash.
- Poll interval: 20 minutes.
- Packet limit: at most 12 cited Bellator items.
- Failed refresh behavior: cached items are explicitly marked `CACHE_FALLBACK`.

Configured enabled RSS sources include:

- BBC World.
- NPR World.
- European Central Bank press releases via official directory discovery.
- European Council press releases.
- European Commission Newsroom.
- United Nations News.
- CISA cybersecurity advisories.
- CSIS.
- Atlantic Council.
- Bellingcat.
- The Record by Recorded Future.
- CyberScoop.

Quarantined or disabled examples:

- Reuters World and Associated Press are quarantined until valid current XML endpoints are confirmed.
- NATO is quarantined while the official directory endpoint requires current XML confirmation.
- Some institutional endpoints are disabled or quarantined after malformed XML, redirect-to-HTML, 403, or 404 probe results.

Probe and polling commands:

```powershell
python tools\probe_rss_feeds.py
python tools\poll_rss_feeds.py --force
python tools\poll_rss_feeds.py --watch
```

GUI data-source actions:

- `Refresh Data Sources`.
- `View Source Health`.
- `View Bellator Intel Feed`.
- `View Aeternum Market Feed`.

## 12. Simulation Layer

The simulation layer is deterministic scaffolding for future scenario and branch analysis. It does not generate autonomous forecasts or invented intelligence.

Current capabilities:

- Scenario records.
- Branch records.
- Simulation type registry.
- Bounded probability and risk scoring helpers.
- Append-only local JSONL history.
- GUI overlays for create/history/branch tree/branch expansion/dossier export.
- Markdown and JSON simulation dossier export.

Important constraint:

- Branch expansion requires explicit operator assumptions.
- The system records deterministic branch probability/risk scaffolding only.

This layer is currently best understood as operator-driven structured foresight scaffolding, not as an autonomous prediction engine.

## 13. AURELIUS and Voice Runtime

AURELIUS is an operator-assistant layer. It is not a tribunal participant, not a provider resolver, and not a replacement for ARBITER.

Current AURELIUS responsibilities:

- Operator acknowledgements.
- Optional voice loop state.
- Optional TTS handoff.
- Explicit routing into existing CONSENSUS handlers only when a handler is attached.
- Telegram assistant operations via `_ARBITER/Bot/aurelius_bot.py`.

Current Telegram state:

- ANIMA is deprecated.
- Active Telegram entrypoint: `_ARBITER/Bot/aurelius_bot.py`.
- Provider routing uses `integrations/msty/aurelius_provider.py`.
- Startup requires `TELEGRAM_BOT_TOKEN`.
- `AURELIUS_TELEGRAM_CHAT_ID` enables scheduled delivery, or `/start` can register chat for the current process.
- Morning Brief is scheduled at `08:00`.
- End-of-Day Shutdown is scheduled at `18:00`.
- Missing/unavailable Msty endpoint is logged once and should not spam scheduled Telegram errors.
- IBKR imports were removed from Telegram startup.

Voice state:

- ARBITER/GLaDOS verdict voice dispatch exists for terminal tribunal outcomes.
- GUI terminal verdict announcements go through the ARBITER voice path rather than AURELIUS.
- Dispatch has once-per-proposal guards.
- Voice dispatch is non-blocking and logs success/failure/degraded states.
- Optional adapters can soft-fail without crashing the GUI.

## 14. Packaging and Executable State

The project includes a PyInstaller one-file Windows operator build:

- `build_exe.py`
- `build_exe.bat`
- `CONSENSUS.spec`
- `packaging/windows_version_info.txt`

Output:

- `dist\CONSENSUS.exe`

The executable uses the same startup flow as `boot.bat`:

- dependency checks,
- Msty provider validation,
- startup theme selection,
- BIOS/POST sequence,
- GUI launch.

Runtime state for frozen builds is written beside the executable where appropriate, while static resources are loaded through PyInstaller extraction paths.

## 15. Evolution Timeline

The project evolved from a legacy/prototype-heavy local system into a modular Python package with strict runtime boundaries, GUI operator tooling, verification manifests, and data-source foundations.

Important phases:

### v7.5.0 modular direction

- Reorganized around modular active source folders.
- Preserved Genesis command entrypoint for compatibility.
- Defined clear ownership for `core`, `config`, `integrations`, `ui`, and `monoliths`.

### v7.10.x hardening and operator workflow

- Added active source integrity manifests.
- Added runtime bundle export.
- Added decision trace viewer.
- Added command palette.
- Added GUI visual/runtime verification.
- Added telemetry collection and dependency diagnostics.
- Stabilized theme/logo rendering and canonical ASCII asset rules.
- Added proposal lifecycle, proposal history, and dossier export.

### v7.11.x simulation, active tribunal flow, GUI refinement

- Added simulation layer foundation.
- Added deterministic branch/scenario scaffolds.
- Improved WAR ROOM layout, headers, telemetry placement, and diagnostics performance.
- Added tribunal lifecycle phases, convergence visualization, and bounded reasoning-state streams.
- Added ARBITER verdict voice dispatch.
- Added AURELIUS runtime tests and provider migration.

### v7.12.x launch and executable phase

- Added canonical `boot.bat` and `boot.ps1`.
- Added diagnostics-only safe mode.
- Added deterministic simulation workflow overlays and export.
- Added standalone PyInstaller executable pipeline and self-test.

### v7.13.x real data and AURELIUS cleanup

- Added normalized data-source registry and cache fallback.
- Added guarded adapters for RSS, GDELT, ACLED, Factal, Ground News, IBKR, and search.
- Established anti-fabrication enrichment behavior.
- Added RSS intelligence backbone with SQLite FTS5 cache, deduplication, probe tools, backoff, and quarantine rules.
- Cleaned up AURELIUS Telegram path, retired active ANIMA bootstrap, removed direct IBKR imports from Telegram startup, and preserved scheduled brief/shutdown flows.

## 16. Strengths

Current strengths:

- Clear modular source layout with active/legacy separation.
- Strong regression coverage across voting, GUI layout, providers, data-source behavior, exports, simulation, telemetry, packaging, and runtime snapshots.
- Health command currently passes.
- Live provider is currently reachable and required models are not missing.
- The system has deterministic mock mode for offline testing and demos.
- Provider fallback and diagnostics are explicit rather than silent.
- Data-source layer is cautious and anti-fabrication oriented.
- RSS sources have quarantine and probe validation instead of hardcoded blind trust.
- GUI has extensive layout and non-overlap regression tests.
- Proposal history and dossier export make decisions auditable and portable.
- The standalone executable path exists and is covered by tests.

## 17. Known Risks and Gaps

Current risks/gaps:

- Provider enumeration latency is high, about 29 seconds in the latest provider check.
- One fast test, `tests\test_health_badge.py`, took about 49 seconds and exceeded the slow threshold.
- Automated screenshot export is not currently a release gate; visual status remains `MANUAL_REVIEW_REQUIRED`.
- Runtime/generated artifacts under `reports/` can dirty the working tree during verification.
- `_ARBITER/` and `archive/` contain large historical/runtime payloads. A prior maintenance audit identified major disk pressure from `_ARBITER/tts_audio/` and `archive/pre_modular_backups/`.
- Some legacy launchers under `_ARBITER` still exist and may contain stale historical assumptions, even though active launchers are modular.
- Credentialed real-data integrations are intentionally disabled until configured; the live external intelligence layer is therefore RSS-first and cache-limited.
- Reuters, AP, NATO, and several institutional feeds remain quarantined until current valid XML endpoints are confirmed.
- AURELIUS Telegram depends on environment configuration and Msty availability.
- The project has many generated runtime files. Commit hygiene needs care before pushing.

## 18. Recommended Next Priorities

Highest-value next work:

1. Reduce provider/status latency.

   The provider check took about 29 seconds. Investigate whether model enumeration can be cached more aggressively, made asynchronous in GUI paths, or split between quick health and full model inventory.

2. Optimize slow fast-category tests.

   `test_health_badge.py` is the main offender at about 49 seconds. The fast suite is passing, but 389 seconds for 205 files is heavy. Health/provider tests should avoid live latency unless explicitly categorized as provider/integration.

3. Decide report artifact hygiene.

   Tests currently update `reports/verification_v7.13.2.json` and generate verdict exports. Decide whether these should be committed as release artifacts, ignored as runtime output, or cleaned after verification.

4. Re-run full verification before a release push.

   Fast verification passed. Full suite, provider category, GUI category, and executable self-test should be run before treating the current tree as release-ready.

5. Complete visual/manual review loop.

   The manifest says screenshots require manual review. Capture and record current GUI screenshots for the active theme families if this version is meant to be finalized visually.

6. Refresh quarantined RSS sources.

   Continue official-directory validation for Reuters, AP, NATO, and other quarantined sources. Only enable feeds that return valid current XML.

7. Add a retention policy for runtime payloads.

   `_ARBITER/tts_audio/`, `_ARBITER/logs/`, `_ARBITER/backups/`, and large archive payloads need explicit retention rules before cleanup.

8. Keep AURELIUS separated from tribunal logic.

   AURELIUS should remain operator-assistant only. Provider truth should stay centralized in Msty runtime/API paths, and market/broker logic should stay behind AETERNUM/integration boundaries.

## 19. What ChatGPT Should Remember

When helping with this project, assume:

- This is a local Windows Python project at `G:\CONSENSUS_SYSTEM`.
- The active package is `consensus-war-room`, version `7.13.2`.
- The system is a multi-agent tribunal, not a single generic chatbot.
- `RATIONALIS`, `AETERNUM`, and `BELLATOR` vote; `ARBITER` synthesizes.
- AURELIUS is an assistant/operator layer and must not be treated as a voting monolith.
- The canonical startup is `boot.bat`; legacy entrypoint compatibility remains via `consensus_war_room_genesis.py`.
- The GUI is Flet-based and delegates to the same tribunal backend.
- The live provider path currently prefers `msty-llama-cpp` at `http://localhost:11454`.
- Mock backend is important for deterministic offline testing.
- Real-data enrichment must never invent intelligence when sources are missing, disabled, stale, or unavailable.
- RSS is the active primary intelligence layer for Bellator; credentialed APIs are enrichment only and disabled by default.
- IBKR is read-only by design and must not place orders.
- Visual/theme assets are important and have many regression contracts. Do not casually replace or regenerate ASCII assets.
- Archive and future implementation folders should not be treated as active source unless explicitly requested.
- Generated runtime artifacts are common; inspect git status before committing.

## 20. Current One-Line Status

CONSENSUS is currently a healthy `v7.13.2` local multi-agent tribunal with passing fast verification, a ready Msty LLaMA.cpp provider, mature GUI/operator workflows, active RSS intelligence scaffolding, deterministic simulation support, executable packaging, and a recently cleaned AURELIUS Telegram assistant path; the main remaining issues are runtime/test latency, manual visual review, generated artifact hygiene, and source/feed quarantine follow-up.
