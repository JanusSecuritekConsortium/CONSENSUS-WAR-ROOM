# CONSENSUS Architecture

This workspace is now organized around the v7.5.0 modular direction while preserving the Genesis command entrypoint used by Msty Studio.

## Runtime Entry Points

- `main.py` is the primary local launcher.
- `consensus_war_room_genesis.py` remains as a compatibility launcher for existing batch files and Msty setup instructions.
- `scripts/start_genesis_api_msty.bat` starts the local API with the Msty/Ollama-compatible backend.

## Current Module Ownership

- `core/models.py`: shared enums and dataclasses for nodes, votes, themes, and tribunal results.
- `config/runtime.py`: runtime settings and config file loading.
- `config/nodes.py`: canonical RATIONALIS, AETERNUM, and BELLATOR identities.
- `core/llm/`: prompt construction and local backend adapters.
- `core/voting/`: vote parsing, quorum rules, confidence scoring, and review triggers.
- `core/voting/orchestrator.py`: routes proposals through runtime-isolated agent sessions.
- `core/voting/engine.py`: pure consensus calculation.
- `core/tribunal.py`: tribunal orchestration and verdict calculation.
- `core/history.py`: audit serialization and legacy history migration.
- `core/memory/store.py`: unified JSON memory store scaffold.
- `core/memory/session.py`: persistent session memory writer and context index maintenance.
- `core/memory/retrieval.py`: keyword/tag/latest-decision retrieval for prior decision context.
- `core/memory/context.py`: context packet facade used by tribunal and GUI proposal flows.
- `core/prompting/assembler.py`: doctrinal monolith prompt assembly.
- `core/knowledge/`: Knowledge Stack source registry and retrieval interfaces.
- `core/health.py`: module health command used by `main.py --health`.
- `core/active_compile.py`: active-source compile boundary for modular code, excluding archive and legacy runtime folders.
- `core/logging.py`: JSONL runtime event logging.
- `integrations/msty/api.py`: FastAPI service, Msty Live Context endpoints, provider discovery, model availability, and provider status.
- `integrations/msty/runtime.py`: Msty session registry, per-agent isolation, fallback policy, streaming facade, and telemetry hooks.
- `integrations/msty/aurelius.py`: AURELIUS operator layer for Msty Claw style workflows.
- `assistant/aurelius_runtime.py`: AURELIUS local assistant runtime for operator acknowledgements, optional voice loop state, TTS handoff, and explicit routing into existing CONSENSUS handlers.
- `assistant/aurelius_persona.yaml`: AURELIUS operator persona and constraints.
- `voice/riko_adapter.py`: optional local voice input adapter for a prepared WAV file or local ASR endpoint, soft-failing when neither is available.
- `voice/attenborough_tts_adapter.py`: optional documentary-style TTS adapter using a configured script, `pyttsx3`, or dry-run manifest output. It is an insertion point for local TTS pipelines and does not clone living-person voices.
- `ui/themes/catalog.py`: canonical theme catalog and aliases.
- `ui/themes/boot_profiles.py`: canonical boot identity profiles for each theme.
- `ui/animations/bios_boot.py`: animated old-BIOS-style runtime boot flow for console and future Flet GUI use.
- `ui/animations/boot.py`: logo loading, terminal boot rendering, Flet-safe logo text options, and theme preview output.
- `ui/animations/loading.py`: theme-specific loading style registry, samples, and console loading animation.
- `ui/animations/typewriter.py`: deterministic text reveal helper for GUI verdict synthesis.
- `ui/war_room_runtime.py`: lightweight GUI activity scheduler primitives for monolith pulse frames, latency display, ambient messages, tribunal timeline entries, proposal lifecycle events, and War Room runtime logging.
- `ui/flet_app.py`: Flet War Room GUI controller, state ownership, status polling, and command handlers.
- `ui/components/`: Flet presentation components for header, monolith cards, proposal input, verdict display, logs, status, and theme switching.
- `ui/rendering.py`: terminal compatibility rendering.
- `monoliths/`: per-monolith profile ownership.

## AURELIUS Assistant Runtime

AURELIUS is an operator-assistant layer, not a tribunal participant and not a provider resolver. It does not perform BIOS checks, provider discovery, model availability checks, or vote parsing. Provider truth remains centralized in the Msty runtime and CLI health paths.

The Flet GUI exposes an `AURELIUS Voice Loop` toggle in the footer. The toggle only updates GUI/runtime assistant state; it does not mutate backend decisions, model configuration, boot provider state, or monolith availability.

Voice behavior is intentionally optional:

- `RikoVoiceAdapter` looks for a prepared voice input file or a local ASR endpoint and soft-fails if neither is present.
- `AttenboroughTTSAdapter` tries a configured local TTS script first, then `pyttsx3`, then writes a dry-run JSON manifest under `_ARBITER/aurelius/`.
- AURELIUS can route text into an attached CONSENSUS handler only when one is explicitly provided.

## Theme and Boot Audit

The active theme catalog contains only the canonical visual identities: MILITARY, EVA, NERV, WH40K, HELLDIVERS, ARASAKA, and JANUS. Aliases resolve to these canonical IDs and do not create duplicate theme records. Each theme defines colors, font family, logo asset, boot profile, loading animation, panel and border style, and monolith display labels.

Boot/loading profiles are centralized in `ui/themes/boot_profiles.py`, with render helpers in `ui/animations/boot.py` and `ui/animations/loading.py`. Large legacy ASCII assets are stored in `static/logos/`; Python code loads them from disk using monospace-preserving text output.

Final visual logo mappings:

- EVA/NERV: `static/logos/nerv_logo.txt`
- ARASAKA: `static/logos/arasaka_logo.txt`
- JANUS: `static/logos/janus_logo.txt`
- WH40K: `static/logos/cogitator_logo.txt` using the supplied industrial block cogitator silhouette.
- HELLDIVERS: `static/logos/helldivers_logo.txt` using the supplied Super Earth command silhouette.
- MILITARY: `static/logos/consensus_logo.txt` using the supplied EXCOMM / CONSENSUS War Room banner.

`eva` and `nerv` remain separate canonical theme IDs for compatibility with existing configs and commands, but they intentionally share the same NERV/MAGI visual family, logo asset, monolith labels, and interface label constants.

The GUI selector exposes visual theme families rather than every compatibility ID. It uses `get_gui_theme_options()` and shows only:

- MAGI Consensus Array (`eva`, covering EVA/NERV aliases)
- Arasaka Executive Tribunal (`arasaka`)
- Janus Security Consortium (`janus`)
- Cogitator Tribunal (`wh40k`)
- Managed Democracy Tribunal (`helldivers`)
- CONSENSUS War Room (`military`)

The `nerv` compatibility theme remains available to CLI commands such as `python main.py --preview-theme NERV` and `python main.py --boot-demo --theme NERV`, but it is not shown as a separate GUI dropdown option.

Use `python main.py --list-themes` to audit the active catalog and `python main.py --preview-theme NERV` to inspect a static theme logo, metadata, boot sample, loading sample, and color set without launching the tribunal.

Use `python main.py --boot-demo --theme NERV` to run the animated old-BIOS-style boot flow. `--speed fast`, `--speed normal`, `--speed slow`, and `--speed random` control console timing. Randomized timing can be reproduced with `--seed`, for example `python main.py --boot-demo --theme JANUS --speed random --seed 42`. The BIOS boot does not depend on live Msty/Ollama provider availability; unavailable external providers are displayed as WARN, not FAIL.

Runtime BIOS tribunal initialization uses a theme-specific boot phrase bank, so RATIONALIS, AETERNUM, BELLATOR, and ARBITER do not repeat the same flavor line every boot. Each visual theme family has 50+ possible node phrases; seeded boot runs remain reproducible for testing while normal boot runs vary naturally.

Use `python main.py --loading-demo --theme NERV` to inspect only the selected theme loading animation without replaying the BIOS stages.

Use `python main.py --gui --theme NERV` to run the selected GUI visual family BIOS boot and launch the Flet War Room GUI. If no theme is supplied, one random GUI visual family is selected once and used for both boot and GUI state. `--compact-header` is accepted for explicit compact header mode and is the default GUI behavior.

GUI window mode is shared across every theme family:

- default / `--maximized`: launches maximized.
- `--fullscreen`: launches fullscreen.
- `--windowed`: launches normal windowed mode for debugging.

Theme selection and live GUI theme switching do not change the active window mode.

The War Room GUI uses a lightweight operational activity layer to keep the existing dashboard alive without changing its layout. Monolith cards receive no-shift pulse glyphs, explicit activity states, tactical latency indicators, and theme-aware idle text. The right-side log panel includes a bounded tribunal timeline for proposal ingestion, vote progress, ARBITER synchronization, ambient heartbeat events, and consensus lock-in.

GUI ambient refresh is deliberately throttled. The War Room updates activity at a calm cadence and refreshes provider/status telemetry less frequently, with a short interaction hold around footer controls so the theme selector is not closed by background repainting while the user is choosing a theme.

Verdict synthesis still uses the established typewriter flow, now with cursor frames, slight pacing variance in interactive use, deterministic no-delay behavior for tests, and a final `[CONSENSUS LOCKED]` state. The verdict panel is the visual focal point of the fixed dashboard: it has the strongest border, a lifecycle banner, larger verdict typography, and idle advisory text so the center panel feels ready instead of empty.

Monolith identity polish stays inside the existing cards. Each monolith has a stable glyph, distinct idle phrases, tactical latency text, and stronger visual treatment only while actively thinking, analyzing, voting, or synchronizing. Proposal input, status metadata, and log formatting are tuned for readability without changing their panel positions.

Runtime activity events are written to `_ARBITER/logs/war_room_runtime.log`; provider/model truth still comes from the central provider resolution layer and is not recalculated by the GUI animation layer. Future audio/TTS hooks are declared as lifecycle names only (`on_proposal_received`, `on_vote_received`, `on_consensus_locked`, `on_error`) and do not play audio in v7.7.1.

Provider readiness includes a short startup grace for the preferred `msty-llama-cpp` inference backend. If the first probe fails during service warm-up, the central provider resolver records a `warming_up` probe, retries up to 3 times with a 2 second delay, and only falls back to Ollama after the retry window fails. Successful warm-up keeps `msty-llama-cpp` as the active backend and reports `READY_AFTER_RETRY`; failed warm-up reports `endpoint unreachable after readiness retry`. The model cache still requires a live reachability check and cannot make an offline backend appear READY.

GUI header logos are intentionally separate from boot/BIOS logos. Full theme logos remain in `static/logos/*.txt` and are used by BIOS boot, preview, and export flows. Dedicated compact GUI header marks live under `static/logos/gui/` and are used only by the Flet header. If a theme has no dedicated GUI header asset, the header falls back to a clipped compact derivation of the full logo while preserving the fixed header box and panel layout.

Dedicated GUI header assets now cover the active visual families:

- EVA/NERV/MAGI: `static/logos/gui/eva_header.txt`
- WH40K/WARHAMMER/COGITATOR: `static/logos/gui/wh40k_header.txt`
- HELLDIVERS/SUPER_EARTH/DEMOCRACY: `static/logos/gui/helldivers_header.txt`
- ARASAKA: `static/logos/gui/arasaka_header.txt`
- MILITARY/EXCOMM: `static/logos/gui/military_header.txt`
- JANUS: `static/logos/gui/janus_header.txt`

Use `python main.py --preview-theme NERV --export-preview` to write text snapshots under `_ARBITER/theme_previews/`. Use `python main.py --export-legacy-visuals` to regenerate `_ARBITER/theme_previews/legacy_visual_reference.txt`.

Normal preview output intentionally shows only the selected theme logo, selected theme BIOS sample, and selected theme loading sample. It must not include `GLOBAL BOOT SAMPLE`, `GLOBAL LOADING SAMPLE`, NERV boot material for non-EVA/NERV themes, or Arasaka loading material for non-ARASAKA themes.

The recovered NERV to Arasaka flow is retained only in `--export-legacy-visuals` as `LEGACY_REFERENCE_SEQUENCE`, where it is reference material, not the active theme boot. The Flet GUI should call `render_bios_boot_flet()` before showing the main War Room UI.

`--boot-demo --theme THEME` is selected-theme scoped:

- MILITARY: `EXCOMM WAR ROOM BIOS`, `INITIALIZING EXCOMM WAR ROOM`
- WH40K: `IMPERIAL COGITATOR BIOS`, `AWAKENING IMPERIAL COGITATOR`
- JANUS: `JANUS DUAL-FRONT BIOS`, `INITIALIZING JANUS MIRROR CHANNEL`
- HELLDIVERS: `SUPER EARTH COMMAND BIOS`, `AUTHORIZING MANAGED DEMOCRACY INTERFACE`
- EVA/NERV: `MAGI / NERV BIOS`, `INITIALIZING MAGI CONSENSUS ARRAY` or `INITIALIZING NERV MAGI INTERLOCK`
- ARASAKA: `ARASAKA EXECUTIVE SECURITY BIOS`, `INITIALIZING ARASAKA EXECUTIVE GRID`

BIOS render order is strict: selected theme logo appears exactly once at the top, followed by a blank line, BIOS identity/header, memory test, device detection, POST, tribunal initialization, theme loading sequence, and handoff. Runtime boot centers the selected theme logo, POST section, and tribunal initialization section. Preview output may show the logo once at the top, but `THEME BIOS SAMPLE` must be generated without repeating that logo.

The BIOS POST provider line is dynamic but compact. It uses the same provider health path as `python main.py --provider-status` and `python main.py --health`, but BIOS output shows only concise status labels. A ready provider renders a theme-specific runtime line such as `[OK] MAGI Runtime` or `[OK] Corporate Runtime`; degraded providers render a compact `[WARN] MSTY PROVIDER DEGRADED` line; offline providers render either a mock-fallback warning or a provider error depending on fallback policy. Detailed provider data such as active backend, endpoint, model count, and missing models belongs in CLI status output and GUI telemetry, not BIOS POST.

Provider resolution is centralized in `integrations/msty/api.py`. `msty-claw` at `http://127.0.0.1:11964` is classified as a Msty Claw / tool orchestration bridge and is not selected for normal model inference unless explicitly requested and inference-compatible. The local model inference path uses `msty-llama-cpp` at `http://localhost:11454`, with `ollama-direct` as the lower-priority fallback. Diagnostics preserve both requested and resolved backend metadata so fallback is visible rather than silent. `--health --verbose`, `--provider-status --verbose`, and `--check-models --verbose` show the probe chain, fallback reason, API shape, model source, service classification, and normalized model alias matches.

Model availability checks perform normalized alias matching before declaring a monolith degraded. This allows configured names such as `yi-34b-chat.Q4_K_S:latest` to match provider-exposed path or GGUF names such as `TheBloke/Yi-34B-Chat-GGUF/yi-34b-chat.Q4_K_S.gguf`.

Provider model enumeration is cached under `_ARBITER/provider_model_cache.json` for a short TTL, defaulting to 120 seconds. Cache entries are keyed by backend, endpoint, and API shape, and store model source, model names, alias matches, timestamp, TTL, original enumeration latency, and cache state. Normal health/model checks use the cache only after a quick reachability check confirms the endpoint is still responding. `--refresh-model-cache` bypasses and replaces the cache.

BIOS headers include the active `SYSTEM_VERSION`, serial/build/theme metadata, and theme-specific authority text. Non-WH40K themes also show the real current local date. WH40K visible boot output keeps Imperial chronology only, using labels such as `DATE REF: 0918015.M03` and `CHRONO-STAMP: 0918015.M03` rather than Gregorian dates. Memory tests are based on detected physical system memory, prefer `psutil` when available, and show MB values rather than fixed kilobyte simulation; if memory detection fails, the fallback is marked clearly.

The animated boot shows `PRESS ENTER TO ENTER THE WAR ROOM` before transferring control to the main interface. The prompt waits for Enter only when the process is attached to an interactive terminal, so automated tests and CI-style command runs do not hang.

Theme resolution is single-source for boot and runtime. If `--theme` is supplied, that canonical theme is used. If no theme is supplied, one random canonical theme is selected and the same theme is carried into the active Consensus interface. Normal interactive Consensus startup uses the same selected-theme BIOS renderer as `--boot-demo`, so the boot theme matches the active Consensus theme.

Console boot logos are colorized by selected theme when `colorama` is available: MAGI/NERV orange-red, Arasaka red, Janus violet-magenta, WH40K aged gold, Helldivers command blue, and Military green/amber. If terminal color support is unavailable, boot output falls back to plain text. Text previews and preview exports remain plain text by default and must not include ANSI escape codes unless a future command explicitly requests colored export.

Console POST and tribunal status checks are rendered with a typewriter-style check cadence. `[OK]` and `ONLINE` status lines are green when console color is available; `[WARN]` and `OFFLINE` status lines are red.

Runtime BIOS boot includes small theatrical diagnostics after control transfer: a theme-prefixed checksum, a brief auxiliary-channel warning, and a final OK lock. These are runtime-only presentation details and are not part of the static preview export contract.

Each canonical theme owns a distinct loading style ID and at least four loading stages:

- MILITARY: `tactical_green_bar` with SYSTEM CHECK, COMMS, MONOLITH LINK, and TACTICAL BUS.
- EVA: `magi_sync_rate` with MAGI LINK, SYNCHRONIZATION RATE, PATTERN ANALYSIS, and INTERLOCK BUS.
- NERV: `nerv_magi_interlock` with MAGI LINK, SYNCHRONIZATION RATE, PATTERN ANALYSIS, and INTERLOCK BUS.
- WH40K: `cogitator_litany` with MACHINE SPIRIT, NOOSPHERIC LINK, DATA-VAULT, and SANCTION PROTOCOL.
- HELLDIVERS: `managed_democracy` with DEMOCRATIC AUTHORIZATION, LIBERTY LOGIC, REQUISITION ACCOUNTING, and STRATAGEM SAFETY.
- ARASAKA: `corporate_clearance_grid` with SECURITY CLEARANCE, COUNTERINTELLIGENCE GRID, CORPORATE NODE, and BOARD VERDICT CHANNEL.
- JANUS: `dual_front_mirror` with DUAL CHANNEL, ANALYTIC MIRROR, COUNTERPART SYNC, and REVERSIBILITY CHECK.

WH40K/Cogitator visual output uses Imperial-style chronology only. Use labels such as `DATE REF: 0918015.M03`, `CHRONO-STAMP: 0918015.M03`, `ARCHIVE DATE: 0918015.M03`, and `NOOSPHERIC TIME INDEX: 0918015.M03`; do not show Gregorian datetimes, UTC/GMT, local clock labels, or standard time strings in WH40K visual surfaces.

## Flet War Room GUI

The Flet GUI is a screen and command surface, not a backend replacement. Components under `ui/components/` contain presentation-only code. Runtime work lives in `ui/flet_app.py`, which delegates proposal submission to the existing tribunal path:

`proposal text -> Tribunal -> VotingOrchestrator -> MstyRuntime -> vote parser -> ConsensusEngine -> decision_history.json`

The GUI layout is organized as fixed regions:

- Header: compact selected-theme logo, system version, active mode, active theme, provider status, memory status, and session id. This region is bounded to roughly 120-150 px and never renders the full boot logo.
- Main body: expanding dashboard row with responsive 20/60/20 left/center/right proportions.
- Footer: fixed compact controls for theme switching, export decision history, export session logs, open theme preview folder, refresh status, launch health check, and shutdown GUI.

The header uses a compact two-part command layout: monospace compact ASCII mark on the left and system telemetry on the right. Full ASCII logos remain owned by boot, preview, and export paths. Header telemetry includes active mode, active theme, provider state, memory, and session id. The page itself is not vertically scrollable by default; only growing content such as live logs and recent decisions scrolls internally.

Monolith cards follow the theme naming doctrine. The theme-specific monolith name is always the primary title, and the canonical system ID appears underneath in smaller text:

- EVA/NERV: MAGI CASPER-3 / RATIONALIS, MAGI BALTHASAR-2 / AETERNUM, MAGI MELCHIOR-1 / BELLATOR.
- WH40K: ADEPTUS MECHANICUS LOGIS / RATIONALIS, ADMINISTRATUM HISTORICUS / AETERNUM, MUNITORUM TACTICUS / BELLATOR.
- ARASAKA: COMPLIANCE LOGIC GRID / RATIONALIS, CAPITAL LEDGER NODE / AETERNUM, COUNTERINTELLIGENCE GRID / BELLATOR.
- JANUS: ANALYTIC MIRROR / RATIONALIS, COUNTERPART HORIZON / AETERNUM, JANUS GATEKEEPER / BELLATOR.
- HELLDIVERS: DEMOCRACY ASSESSMENT ENGINE / RATIONALIS, FREEDOM FORECASTING SYSTEM / AETERNUM, LIBERTY DEFENSE MATRIX / BELLATOR.
- MILITARY: LOGICAL ANALYSIS MATRIX / RATIONALIS, ECONOMIC INTELLIGENCE DIVISION / AETERNUM, TACTICAL OPERATIONS CENTER / BELLATOR.

ARBITER uses theme-specific labels if they are later added; otherwise it falls back to ARBITER / CONTROL CORE. State borders and glyphs distinguish ONLINE, THINKING, DEGRADED, OFFLINE, ERROR, and vote states without changing the backend decision path. The left column also includes a bounded `TRIBUNAL READINESS` block for SESSION, MEMORY, THEME, PROVIDER, LAST VERDICT, and LIFECYCLE. Readiness rows are compact and scroll inside the panel if the available height is too small, so long WH40K/Cogitator values cannot draw outside the panel border.

Themes expose contrast-safe text tokens for GUI surfaces: `muted_text`, `secondary_text`, `panel_label`, and `panel_value`. Readiness and status panels use these tokens instead of structural colors, so dark themes such as ARASAKA can keep black/red borders while still rendering readable labels and values.

The center column gives more space to the live work surface. Proposal input and verdict output use proportional expansion so the verdict panel remains prominent without leaving the pre-submission area empty.

The verdict panel is the center of gravity for tribunal output. It shows the current proposal, verdict, confidence bar, per-monolith vote vector, and ARBITER synthesis text. While idle it displays a cursor-like waiting state.

During proposal submission, the GUI exposes a live deliberation lifecycle:

- `IDLE`
- `PROPOSAL RECEIVED`
- `MONOLITHS DELIBERATING`
- `VOTES RECEIVED`
- `ARBITER SYNTHESIZING`
- `VERDICT ISSUED`
- `ERROR / DEGRADED`

RATIONALIS, AETERNUM, and BELLATOR enter `THINKING` when a proposal starts. Each monolith card then reveals its vote, confidence, response time, and a short reasoning snippet as that vote is received. ARBITER enters synthesis mode after votes are collected.

The ARBITER synthesis text uses the typewriter helper for live GUI display. Tests and non-interactive paths can skip the delay deterministically. The confidence bar uses displayed-confidence state so it can animate toward the final confidence value and color itself by confidence band: primary/accent for high, warning for medium, and error for low/error confidence.

Live logs are read from the JSONL system log and rendered with timestamps, internal auto-scroll, and level-aware colors. INFO, WARN, ERROR, SUCCESS/OK, DECISION, and VOTE events receive distinct color categories. Recent decisions render as individual verdict-colored rows so approvals, denials, deadlocks, and review states are visually separable.

Ambient GUI heartbeat text rotates without writing to logs. Current messages include `MONOLITH LINK STABLE`, `MEMORY INDEX READY`, `PROVIDER CHECK PENDING`, and `TRIBUNAL IDLE`.

Theme switching in the GUI uses a compact fixed-width footer selector populated by GUI visual families, not every compatibility alias. It updates UI colors, labels, borders, and logo live. It does not rewrite persisted runtime config or mutate previous backend decisions. New submissions use the current GUI state theme.

Provider degradation is visible but non-fatal. If Msty/Ollama is unavailable, the GUI still launches and proposal submission can proceed through the configured mock or runtime fallback behavior. When fallback is active, the GUI displays `PROVIDER DEGRADED - MOCK FALLBACK ACTIVE`.

The footer includes `RECHECK PROVIDER`, which refreshes provider status, monolith availability, header telemetry, and status panel state without changing the active theme or window mode.

Provider discovery probes local Msty/Ollama-compatible endpoints and labels the reachable runtime, not merely the requested backend. Precedence is: explicit `MSTY_BASE_URL` if reachable, configured `msty_base_url`, default Msty Local AI Service `http://localhost:11964`, configured or explicit Ollama, default Ollama Direct `http://127.0.0.1:11434`, then Msty LLaMA.cpp only when explicitly configured or selected. If Msty is unavailable but Ollama answers `/api/tags`, active backend becomes `ollama-direct` without restarting the GUI. LLaMA.cpp at `http://localhost:11454` is treated as a lower-level/model-specific endpoint, not the default CONSENSUS service.

Provider status includes backend, endpoint, ready/degraded/offline state, latency in milliseconds, available model count, required model map, missing required models, and fallback/strict-mode policy. Required models are checked for RATIONALIS, AETERNUM, BELLATOR, and ARBITER. If a monolith model is missing, the GUI marks that monolith DEGRADED and displays the missing model in the card details.

Fallback policy:

- Real mode: provider is ready and required models exist, so real provider execution is used.
- Degraded mode: provider is reachable but one or more required models are missing; available models are used and missing monoliths fall back to mock when fallback is enabled.
- Degraded model remap mode: `use_available_model_fallback` is enabled and at least one provider model exists, so missing required models are temporarily routed to the first available model and the GUI displays `MODEL REMAP ACTIVE`.
- Offline mode: provider cannot be reached; all monoliths use mock fallback when fallback is enabled.
- Strict mode: missing provider or required model availability fails instead of falling back.

Use these CLI commands without launching the GUI:

```powershell
python main.py --provider-status
python main.py --provider-diagnose
python main.py --list-models
python main.py --check-models
python main.py --set-all-models mistral:latest
python main.py --set-model RATIONALIS deepseek-coder-33b-instruct.Q4_K_S:latest
python main.py --show-model-config
```

Runtime config supports:

```json
{
  "msty_base_url": "http://localhost:11964",
  "ollama_base_url": "http://127.0.0.1:11434",
  "msty_llama_cpp_base_url": "",
  "mock_fallback_enabled": true,
  "strict_provider_mode": false,
  "use_available_model_fallback": false
}
```

Status polling is lightweight and non-blocking: provider status, memory status, recent logs, recent decisions, and monolith availability refresh from a background thread and update the page through Flet-safe callbacks.

## Persistent Memory and Prompt Context

CONSENSUS keeps persistent reasoning memory in:

- `_ARBITER/decision_history.json`: existing decision audit log.
- `_ARBITER/memory/session_memory.json`: session-level proposal, vote, verdict, provider, model, context, and tag memory.
- `_ARBITER/memory/context_index.json`: readable keyword/tag index rebuilt from session memory.

Session memory writes use atomic temporary-file replacement. If a session memory file is malformed, it is moved to a `.bak` corruption backup and a clean empty memory object is used. Memory failures are logged as WARN in GUI flows rather than crashing the War Room.

Context retrieval is intentionally simple in v7.5.0: keyword overlap, tag overlap, and latest prior decisions. There is no vector database yet. Retrieved context is inserted into monolith prompts as a short packet and displayed in the verdict panel as `Context used: N prior decisions`.

Doctrinal behavior lives under `monoliths/profiles/`:

- `rationalis.json`
- `aeternum.json`
- `bellator.json`
- `arbiter.json`

These profiles define canonical ID, display role, doctrine, preferred reasoning style, risk bias, evidence weighting, and escalation behavior. UI theme language is deliberately excluded from doctrinal profiles.

Prompt assembly combines the proposal, selected model, doctrinal profile, retrieved memory context, shared machine context, and the existing parseable vote schema. The output schema remains compatible with the current vote parser.

Memory CLI commands:

```powershell
python main.py --memory-status
python main.py --session-summary
python main.py --export-session
python main.py --search-decisions "query text"
```

## Active Compile Boundary

`python main.py --compile-active` compiles only active modular source: `main.py`, `consensus_war_room_genesis.py`, `core/`, `config/`, `integrations/`, `ui/`, `monoliths/`, `tests/`, and `scripts/`. It intentionally excludes `archive/`, `_ARBITER/`, generated caches, and legacy broken files. Health checks fail on active compile errors but may report `DEGRADED` when the external Msty/Ollama provider is unavailable.

## Archive and Root Hygiene

Root is reserved for current launchers and documentation. Allowed root Python files are `main.py` and `consensus_war_room_genesis.py`. Historical monoliths, old launchers, imported demos, experiments, generated root caches, and pre-modular backups belong under `archive/`.

No archived file is deleted during cleanup. Every moved root entry is recorded in `archive/ARCHIVE_MANIFEST.md` with original path, new path, reason, active-code reference status, and deletion confidence. `tests/test_root_hygiene.py` fails if obsolete Python files return to the root.

## Refactor Rule

New implementation belongs in the owning module above. Runtime owns sessions. Voting owns decisions. Memory owns persistence. UI only observes and sends commands. Legacy files can remain as references, but new behavior should not be added to the old war-room monoliths.

## Near-Term Build Order

1. Add model health checks before deliberation and exclude unavailable monoliths automatically.
2. Move terminal rendering behind a Flet GUI shell instead of expanding CLI output.
3. Add an async event bus for UI state, API requests, model health, and telemetry.
4. Expand Knowledge Stack retrieval beyond metadata-only source matching.
