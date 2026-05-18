# Changelog

## 7.7.7 - War Room Refresh Cadence and Boot Phrase Variation

- Reduced automatic GUI page rebuild cadence so footer controls and the theme selector are no longer interrupted by aggressive background refresh.
- Added an interaction hold around the GUI theme dropdown so ambient/status polling does not steal focus while the user is selecting a theme.
- Added a theme-specific BIOS node phrase bank with 50+ possible boot phrases per visual family; runtime boot now selects deterministic seeded or randomized phrases while static previews remain stable.
- Added regression coverage for GUI refresh cadence and boot phrase variation.

## 7.7.6 - Original Compact Header Logo Redesign

- Replaced the previous EVA, WH40K, and HELLDIVERS compact GUI headers with stronger original ASCII marks.
- Kept all changes confined to GUI-only compact header assets; boot, BIOS, preview, export, provider, and War Room runtime behavior remain unchanged.

## 7.7.5 - Originalized Compact Header Marks

- Replaced the EVA, WH40K, and HELLDIVERS compact GUI header examples with original compact marks inspired by each theme's operational identity.
- Kept the same GUI-only asset paths and left all boot, BIOS, preview, and export logos unchanged.

## 7.7.4 - Expanded GUI Compact Header Logos

- Added dedicated GUI-only compact header logo assets for EVA/NERV/MAGI, WH40K/Cogitator, and HELLDIVERS/Managed Democracy.
- Extended the GUI compact logo registry so EVA and NERV share `eva_header.txt`, WH40K aliases resolve to `wh40k_header.txt`, and HELLDIVERS aliases resolve to `helldivers_header.txt`.
- Kept boot, BIOS, preview, and export flows on their full theme logo assets.
- Added alias regression coverage for EVA/NERV/MAGI, WH40K/WARHAMMER/COGITATOR, and HELLDIVERS/SUPER_EARTH/DEMOCRACY.

## 7.7.3 - GUI Compact Header Logos

- Added dedicated GUI-only compact header logo assets under `static/logos/gui/` for ARASAKA, MILITARY, and JANUS.
- Updated the Flet header to prefer dedicated GUI compact logos while preserving the existing derived compact fallback for themes without a dedicated asset.
- Kept boot, BIOS, preview, and export logos on the full `static/logos/*.txt` assets.
- Centered compact header logo content inside the existing logo box without resizing the header or changing War Room layout structure.
- Added regression coverage proving dedicated compact assets are selected, full boot logos are not used in the GUI header when a compact logo exists, and compact logos fit declared header constraints.

## 7.7.2 - Msty LLaMA.cpp Readiness Retry

- Added a short readiness retry window for `msty-llama-cpp` so temporary startup races do not immediately force Ollama fallback.
- `msty-llama-cpp` now reports intermediate `warming_up` probe entries and retries up to 3 times with a 2 second delay before declaring the endpoint unreachable.
- If the backend becomes ready during retry, the active backend remains `msty-llama-cpp`, fallback stays inactive, and diagnostics report `READY_AFTER_RETRY`.
- If retry fails, fallback remains transparent with reason `endpoint unreachable after readiness retry`.
- Provider verbose diagnostics and health verbose output now include readiness retry metadata.
- Cached model lists are still gated by live reachability; stale cache is not used as proof of readiness while a backend is offline or warming.
- Added readiness retry, warmup state, retry-before-fallback, and cache-safety regression tests.

## 7.7.1 - War Room Visual Polish

- Strengthened GUI visual hierarchy without changing layout: ARBITER verdict now has stronger border weight, larger verdict typography, more internal breathing room, and a theme-aware lifecycle banner.
- Improved proposal input ergonomics with clearer placeholder text, focused border/cursor colors, padding, monospace text styling, and the `CTRL+ENTER = Submit to Tribunal` hint.
- Added active monolith emphasis for thinking/analyzing/voting/synchronizing states via stronger borders, intensified pulse markers, brighter titles, distinct monolith glyphs, and monolith-specific idle phrases.
- Cleaned up the right-side status panel into Provider, Memory, Context, and Lifecycle sections while preserving diagnostic metadata.
- Made log display more compact for repeated health, vote, and verdict events while preserving tail behavior and severity colors.
- Added future lifecycle hook declarations for proposal received, vote received, consensus locked, and error cues without implementing audio.
- Added visual hierarchy, proposal ergonomics, monolith identity, status section, and lifecycle hook regression tests.

## 7.7.0 - War Room Operational Presence

- Added lightweight War Room activity pulses, tactical latency indicators, and idle activity text for monolith cards without changing the GUI layout structure.
- Added explicit GUI monolith activity states: `IDLE`, `THINKING`, `ANALYZING`, `VOTING`, `SYNCHRONIZING`, `ERROR`, and `OFFLINE`.
- Added a bounded tribunal timeline feed inside the existing logs panel for proposal ingestion, vote progress, ARBITER synchronization, ambient heartbeat events, and consensus lock-in.
- Enhanced verdict synthesis typing with cursor frames, deterministic test mode, slight pacing variance, and final `[CONSENSUS LOCKED]` state.
- Added theme-specific ambient messages for MILITARY, EVA/NERV, WH40K, HELLDIVERS, ARASAKA, and JANUS.
- Added `_ARBITER/logs/war_room_runtime.log` for GUI state transitions, proposal lifecycle events, ambient heartbeats, and UI refresh anomalies.
- Added regression coverage for the War Room state machine, verdict typing animation, idle pulses, ambient messages, and proposal lifecycle flow.

## 7.6.2 - Provider Model Cache

- Added a short-lived disk-backed provider model cache keyed by backend, endpoint, and API shape.
- Default model cache TTL is 120 seconds and can be overridden with `CONSENSUS_MODEL_CACHE_TTL` or runtime config.
- Added `--refresh-model-cache` to bypass cache, perform live model enumeration, and replace the cached entry.
- Provider status, model checks, health, GUI startup health, and runtime health now reuse cached model lists after confirming the endpoint is still reachable.
- Verbose diagnostics now show model cache hit/miss/refresh state, cache age, TTL, original enumeration latency, and current check latency.
- Cache safety rule: stale cache is never used as READY health truth when the backend endpoint is unreachable.
- Added model cache regression coverage for cache hits, refresh bypass, offline safety, health reuse, and backend/endpoint cache separation.

## 7.6.1 - Provider Resolution and Diagnostic Clarity

- Fixed backend resolution so explicit CLI/runtime backend selection is probed first, followed by `msty-local`, `msty-llama-cpp`, `ollama-direct`, then mock fallback if enabled.
- Promoted reachable Msty LLaMA.cpp service at `http://localhost:11454` ahead of Ollama direct fallback when Msty Local AI at `http://localhost:11964` is offline.
- Added transparent provider fallback metadata: requested backend/endpoint/status, resolved backend/endpoint, fallback activation, fallback reason, probe chain, API shape, and model source.
- Clarified Msty roles: `msty-claw` at `http://127.0.0.1:11964` is treated as a tool/orchestration bridge, while `msty-llama-cpp` at `http://localhost:11454` is the default local model inference runtime.
- Added model alias matching before declaring configured monolith models missing, including GGUF/path-style model names and normalized quantization suffixes.
- Added `--verbose` provider diagnostics for `--health`, `--provider-status`, and `--check-models`.
- Preserved the v7.5.3 BIOS/provider synchronization rule: BIOS consumes the central resolved provider object and performs no independent provider checks.
- Added regression coverage for backend override priority, fallback chain ordering, Msty LLaMA.cpp preference, and v7.6.1 provider consistency.

## 7.6.0 - AURELIUS Assistant Runtime

- Added the `assistant/` runtime layer for AURELIUS operator assistance without introducing any independent provider, model, or BIOS health checks.
- Added `assistant/aurelius_persona.yaml` to define AURELIUS as an operator assistant that can acknowledge requests and optionally route work through the existing CONSENSUS path.
- Added `voice/attenborough_tts_adapter.py` with configured-script, local `pyttsx3`, and dry-run manifest output modes. The adapter provides calm documentary-style pacing hooks and does not clone living-person voices.
- Added `voice/riko_adapter.py` for optional local push-to-talk/ASR input, with soft failure when no audio file or ASR endpoint is available.
- Added an AURELIUS Voice Loop toggle to the Flet War Room footer, wired to GUI state and runtime state without changing tribunal voting or provider resolution.
- Added active compile coverage for `assistant/` and `voice/`, plus runtime and GUI toggle regression tests.

## 7.5.3 - Boot Provider Resolution Consistency

- Removed independent provider/model probing from the BIOS boot renderer.
- Routed boot-demo, GUI boot, and normal interactive boot through the same resolved provider object used by provider status and model checks.
- Added regression coverage proving READY provider state renders `[OK]` in BIOS POST, degraded state does not survive through stale cache, and BIOS code has no independent Ollama/Msty fallback path.

## 7.5.2 - BIOS Logo Spacing Polish

- Added two renderer-level blank lines between the full BIOS logo block and BIOS header for all themes.
- Added BIOS formatting coverage to keep logo assets untouched while preserving clearer boot composition spacing.

## 7.5.1 - ASCII Logo Whitespace Preservation

- Fixed BIOS logo centering so ASCII assets keep their original leading whitespace instead of being stripped before rendering.
- Refined BIOS logo rendering to center each ASCII logo as a single preformatted block with outer padding only, preserving internal wordmark alignment.
- Centered the BIOS header block during runtime boot demos so the header no longer snaps to column zero after a centered logo.
- Verified the Arasaka logo asset remains in its supplied legacy shape and added regression coverage across all boot logo assets.
- Added tests to prevent logo loaders from using full-content strip/dedent/lstrip normalization.

## 7.5.0 - Persistent Memory and Doctrinal Reasoning Stack

- Added persistent session memory at `_ARBITER/memory/session_memory.json` and context index generation at `_ARBITER/memory/context_index.json`.
- Added keyword/tag/latest-decision context retrieval for prior proposals and decisions before monolith voting.
- Added doctrinal monolith profiles for RATIONALIS, AETERNUM, BELLATOR, and ARBITER under `monoliths/profiles/`.
- Added prompt assembly that combines proposal, monolith doctrine, selected model, retrieved memory context, and the existing parseable vote schema.
- Added GUI memory indicators for session memory, context retrieval, prior decisions used, and current session id.
- Added memory CLI commands: `--memory-status`, `--session-summary`, `--export-session`, and `--search-decisions`.
- Added regression tests for session memory, context retrieval, prompt assembly, monolith profiles, memory CLI, and GUI memory indicators.

## 7.4.9 - Msty Endpoint Diagnostics

- Clarified provider endpoint roles: Msty Local AI Service at `http://localhost:11964`, Ollama Direct at `http://127.0.0.1:11434`, and Msty LLaMA.cpp Service at `http://localhost:11454`.
- Updated provider priority so Msty Local AI Service remains the default CONSENSUS endpoint, Ollama Direct is the fallback, and LLaMA.cpp is only used when explicitly configured or selected.
- Added `--provider-diagnose` to probe known endpoints and report reachability plus `/api/tags` and `/v1/models` API shapes.
- Added optional `msty_llama_cpp_base_url` and `--msty-llama-cpp-base-url` for explicit lower-level backend selection.
- Added provider diagnostics regression coverage.

## 7.4.8 - BIOS POST Presentation Cleanup

- Shortened BIOS provider POST output to compact theme-specific runtime labels such as `MAGI Runtime`, `Corporate Runtime`, and `Cogitator Runtime`.
- Removed provider endpoint, backend, and model-count details from BIOS POST output; detailed provider data remains in CLI and GUI telemetry.
- Restored consistent block-centering for POST lines by centering trimmed POST entries as one fixed-width block.
- Added BIOS POST formatting coverage for compact runtime labels, endpoint suppression, centering, and GUI provider detail preservation.

## 7.4.6 - Dynamic BIOS Provider POST

- Replaced the hardcoded BIOS provider warning with a dynamic POST line sourced from the same provider health path used by `--provider-status` and `--health`.
- BIOS POST now reports provider READY as `[OK]`, DEGRADED as `[WARN]`, and OFFLINE as either fallback warning or provider error depending on fallback policy.
- Added provider boot context fields for active backend, endpoint, status, model count, and missing model count.
- Added deterministic BIOS provider status tests for ready, degraded, offline fallback, and offline strict paths.

## 7.4.5 - Per-Monolith Model Assignment CLI

- Added `--set-model MONOLITH MODEL` for persistent ARBITER, RATIONALIS, AETERNUM, and BELLATOR model assignment.
- Added `--show-model-config` to print the effective configured model per monolith.
- Kept `--set-all-models MODEL` for quick testing and bulk remap setup.
- Added validation for unknown monolith names and provider availability warnings when a selected model is not currently listed.
- Added regression coverage for per-monolith model assignment, model config display, unknown-monolith rejection, unavailable-model warnings, and `--check-models` success with configured available models.

## 7.4.4 - Ollama Direct Runtime Fallback

- Added active provider probing with Msty-first and Ollama-direct fallback precedence.
- Labeled reachable Ollama endpoints as `ollama-direct` in CLI, provider payloads, and GUI status output.
- Added default Ollama fallback endpoint `http://127.0.0.1:11434` while keeping Msty at `http://127.0.0.1:11964`.
- Added `use_available_model_fallback` for temporary degraded model remapping to the first available provider model.
- Added `--set-all-models MODEL` to persistently update ARBITER and tribunal monolith model overrides.
- Added Ollama-direct backend and model-remap regression tests.

## 7.4.3 - Safe Provider CLI Offline Handling

- Hardened provider model discovery so offline Msty/Ollama endpoints return structured OFFLINE payloads instead of leaking raw connection exceptions.
- Updated `--list-models`, `--provider-status`, and `--check-models` to print endpoint, model count, and offline guidance without a traceback.
- Normalized request connection, timeout, and request failures in the Ollama-compatible backend.
- Added offline provider CLI regression coverage using mocked connection failures.

## 7.4.2 - Arasaka Contrast Tokens

- Added contrast-safe theme text tokens for muted text, secondary text, panel labels, and panel values.
- Updated readiness and status panels to use readable panel text tokens instead of structural dark colors.
- Improved ARASAKA left-panel contrast so readiness labels and values remain visible on dark corporate panels.
- Added contrast-token tests covering ARASAKA readability and readiness row color binding.

## 7.4.1 - GUI Readiness Containment

- Compacted the left-column `TRIBUNAL READINESS` rows to short labels: SESSION, MEMORY, THEME, PROVIDER, LAST VERDICT, and LIFECYCLE.
- Made readiness rows scroll inside the bounded panel so long WH40K status values cannot render outside the border.
- Tightened readiness typography and spacing while preserving the expanding left-column layout.
- Added WH40K-focused readiness containment regression coverage.

## 7.4.0 - Msty Provider Hardening

- Added structured provider discovery for Msty/Ollama-compatible endpoints, including endpoint resolution, available models, latency, model count, missing required models, and ready/degraded/offline state.
- Added endpoint precedence: `MSTY_BASE_URL`, then `OLLAMA_BASE_URL`, then `_ARBITER/genesis_config.json` values.
- Added `mock_fallback_enabled` and `strict_provider_mode` runtime config options.
- Added CLI provider commands: `--provider-status`, `--list-models`, and `--check-models`.
- Hardened `MstyRuntime` fallback policy so missing/offline models use mock fallback when enabled and fail in strict mode.
- Updated GUI provider panel with endpoint, latency, available model count, missing models, and fallback state.
- Updated provider recheck to refresh model availability and mark monoliths degraded when required models are missing.
- Added Windows-safe unique temp file/retry behavior for decision history writes.
- Added provider discovery, model availability, fallback policy, and GUI provider status panel tests.

## 7.3.6 - GUI Hierarchy and Monolith Naming Doctrine

- Changed GUI monolith cards to lead with the selected theme's monolith name and show the canonical system ID underneath.
- Applied the naming hierarchy across EVA/NERV, WH40K, ARASAKA, JANUS, HELLDIVERS, MILITARY, and ARBITER fallback cards.
- Added tactical status color categories and state glyphs for ONLINE, THINKING, DEGRADED, OFFLINE, ERROR, and vote states.
- Added lifecycle to the tribunal readiness block and improved readiness row spacing/markers.
- Refined log severity color handling for INFO, WARN, ERROR, SUCCESS/OK, DECISION, and VOTE events.
- Added ambient GUI heartbeat text rotation without log spam.
- Added monolith naming, status color, and heartbeat regression tests.

## 7.3.5 - Live Deliberation Behavior

- Added GUI proposal lifecycle states: IDLE, PROPOSAL RECEIVED, MONOLITHS DELIBERATING, VOTES RECEIVED, ARBITER SYNTHESIZING, VERDICT ISSUED, and ERROR / DEGRADED.
- Added live monolith states so RATIONALIS, AETERNUM, and BELLATOR show THINKING during submission and then reveal vote, confidence, reasoning snippet, and response time.
- Added `ui/animations/typewriter.py` for deterministic async/sync synthesis text reveal.
- Animated GUI confidence display through a displayed-confidence state with theme-colored confidence levels.
- Updated verdict and status panels to show lifecycle state and degraded fallback messaging.
- Added `RECHECK PROVIDER` to refresh provider status, monolith availability, header telemetry, and status panel state.
- Kept degraded provider operation non-fatal with visible `PROVIDER DEGRADED - MOCK FALLBACK ACTIVE` messaging.
- Added tests for live deliberation states, typewriter behavior, and provider recheck/fallback.

## 7.3.4 - Fullscreen War Room Layout

- Added GUI window mode flags: `--fullscreen`, `--maximized`, and `--windowed`.
- Made maximized mode the default for every GUI theme family, with fullscreen/windowed behavior handled in shared Flet setup.
- Rebalanced the dashboard body into responsive 20/60/20 left/center/right regions instead of fixed narrow side columns.
- Reduced the compact header height and added `ACTIVE MODE: GUI WAR ROOM` to telemetry.
- Added a left-column `TRIBUNAL READINESS` block so the monolith column uses available vertical space.
- Split the center column into proposal and verdict regions with proportional expansion.
- Added window-mode and responsive-layout regression tests.

## 7.3.3 - GUI Footer and Decision Polish

- Reduced the GUI footer theme selector footprint with a dense fixed-width dropdown.
- Kept the GUI selector de-duplicated so the EVA/NERV family appears only as `MAGI Consensus Array`.
- Rendered recent decisions as individual rows with verdict-aware colors for faster scanning.
- Added regression coverage for compact selector sizing and verdict-colored recent decisions.

## 7.3.2 - GUI Theme Selector De-Duplication

- Added `get_gui_theme_options()` for GUI-facing visual theme families.
- Collapsed EVA/NERV into one GUI selector entry, `MAGI Consensus Array`, while keeping internal `nerv` compatibility for boot and preview commands.
- Updated the GUI theme switcher to show display names only and store canonical GUI family IDs internally.
- Routed `--gui --theme NERV` through the MAGI GUI family so boot and GUI runtime theme remain aligned.
- Added GUI theme selector tests covering duplicate removal, hidden aliases, NERV compatibility, MAGI styling, and boot-to-GUI alignment.

## 7.3.1 - GUI Layout Containment

- Bounded the Flet War Room header to a compact fixed-height region so the main dashboard is visible without scrolling past the logo.
- Switched the GUI header to compact logo rendering; full ASCII logos remain reserved for BIOS boot, static preview, and text exports.
- Reworked the GUI shell into fixed header, expanding main body, and fixed footer regions.
- Disabled page-level vertical scrolling by default and kept scrolling inside log/recent-decision content.
- Added `python main.py --gui --theme EVA --compact-header` compatibility for the compact header path, which is now the default.
- Added a GUI layout contract test for bounded header height, compact logo use, expanding body, internal log scrolling, and no default page scroll.

## 7.3.0 - Flet War Room GUI

- Added `python main.py --gui` to run the selected-theme BIOS boot and then launch the Flet War Room GUI.
- Added modular Flet GUI shell in `ui/flet_app.py` with components under `ui/components/`.
- Added GUI panels for header/status, monolith cards, proposal submission, verdict display, logs, recent decisions, and theme switching.
- Kept backend ownership outside components: GUI proposal submission routes through `Tribunal -> MstyRuntime -> VotingOrchestrator -> ConsensusEngine -> decision_history.json`.
- Added lightweight GUI status refresh for provider health, memory status, recent logs, recent decisions, and monolith availability.
- Added GUI export actions for decision history, current session logs, and opening the theme preview folder.
- Bound GUI theme state to the same boot-selected canonical theme, with live theme switching limited to UI state.
- Added Flet import, GUI theme binding, and GUI mock submission tests.
- Tuned BIOS boot presentation with tighter logo/header spacing, fixed-block MB memory checks, shorter provider warning text, theme-specific loading bar labels, staggered ONLINE timing, and runtime checksum/recalibration diagnostics.
- Refined the Flet War Room surface with a logo-plus-telemetry header, exact-width ASCII logo preservation, stronger monolith card hierarchy, terminal-styled buttons, confidence/vote breakdown in the verdict panel, and timestamped level-aware live logs.

## 7.2.6 - Centered BIOS Boot and Interactive Handoff

- Centered selected-theme logos in the animated BIOS boot renderer while keeping static logo assets unchanged.
- Added real build/version metadata to BIOS headers, plus real local date for non-WH40K themes.
- Changed memory test output from fixed kilobyte simulation to detected system memory in MB, preferring `psutil` when available and marking fallback memory clearly.
- Centered POST and tribunal initialization sections in boot output.
- Added console status coloring for `[OK]` and `ONLINE` lines, with `[WARN]` and `OFFLINE` shown in red when `colorama` is available.
- Added typewriter-style rendering for POST and tribunal status checks.
- Slowed boot/loading timing slightly and kept randomized loading speed reproducible with `--seed`.
- Added a non-blocking-in-automation user interaction prompt, `PRESS ENTER TO ENTER THE WAR ROOM`, before transferring control to the main Consensus interface.
- Routed normal interactive Consensus startup through the selected-theme BIOS boot renderer so boot visuals match the active theme.
- When no theme is supplied, boot resolves one random canonical theme and carries that same theme into the active runtime interface.

## 7.2.5 - Theme-Colored Logos and Loading Bars

- Colorized console boot logos by selected theme when `colorama` is available, with plain-text fallback.
- Updated Flet boot preparation so logo text uses theme color metadata while preserving monospace spacing.
- Replaced the generic boot loading bar with theme-specific loading styles, labels, stages, and bar formats.
- Added `--speed random` and `--seed` support for reproducible randomized boot/loading timing.
- Added `python main.py --loading-demo --theme THEME` for isolated loading animation checks.
- Kept text previews and exported preview snapshots free of ANSI color codes by default.
- Added tests for unique loading style IDs, theme-specific loading stages, seeded random timing, WH40K visual language, and plain-text exports.
- Replaced WH40K, HELLDIVERS, and MILITARY logo assets with the final supplied ASCII/UTF-8 silhouettes and added regression coverage for those shapes.
- Changed Helldivers to a blue/white command palette and moved Janus to a distinct violet-magenta palette so their logo colors do not overlap.

## 7.2.4 - BIOS Render Order and Logo De-Duplication

- Refactored BIOS boot generation so the selected theme logo renders once at the top before the BIOS header.
- Removed repeated logo rendering after tribunal initialization and before loading.
- Added `include_logo` and `include_loading` controls to `generate_bios_boot_lines(...)` for preview/export reuse.
- Updated static theme previews so `THEME BIOS SAMPLE` does not repeat the logo already shown at the top.
- Added theme-specific authority lines for EVA/NERV, ARASAKA, JANUS, WH40K, HELLDIVERS, and MILITARY BIOS headers.
- Added tests for logo order, logo de-duplication, preview sample de-duplication, and WH40K Imperial visible time.

## 7.2.3 - Theme-Scoped Preview and Boot Correction

- Removed global NERV/Arasaka samples from normal `--preview-theme` output.
- Normal previews now show only selected theme logo, metadata, labels, colors, `THEME BIOS SAMPLE`, and `THEME LOADING SAMPLE`.
- Kept the old NERV to Arasaka sequence only in `--export-legacy-visuals` as `LEGACY_REFERENCE_SEQUENCE`.
- Updated `--boot-demo --theme THEME` to use selected-theme BIOS headers, selected-theme display device labels, selected-theme logo, and selected-theme loading labels.
- Added regression tests for preview contamination and selected-theme boot samples.

## 7.2.2 - BIOS-Style Animated Boot

- Added `ui/animations/bios_boot.py` with console and Flet-ready BIOS boot renderers.
- Added `python main.py --boot-demo`, with `--theme` and `--speed fast|normal|slow` options.
- Added generated BIOS boot stages for memory testing, device detection, POST, tribunal initialization, NERV logo handoff, and Arasaka loading.
- Kept `--preview-theme` as a static visual inspection command; animated runtime boot now lives under `--boot-demo`.
- Added `tests/test_bios_boot.py` to verify boot content and provider-independent WARN behavior.
- Finalized logo mappings: EVA/NERV use `nerv_logo.txt`, ARASAKA uses `arasaka_logo.txt`, JANUS uses `janus_logo.txt`, WH40K uses `cogitator_logo.txt`, HELLDIVERS uses `helldivers_logo.txt`, and MILITARY uses `consensus_logo.txt`.
- Changed normal theme previews to show only the selected theme logo, selected theme BIOS sample, and selected theme loading sample.
- Limited the recovered NERV to Arasaka sequence to `--export-legacy-visuals` under `LEGACY_REFERENCE_SEQUENCE`.
- Added WH40K/Cogitator Imperial timestamp language using `0918015.M03` for visual output.

## 7.2.1 - Active Compile Boundary and Legacy Visual Recovery

- Added `python main.py --compile-active` for active modular source compilation without traversing `archive/`, `_ARBITER/Bot/`, generated caches, or legacy broken files.
- Added health-check coverage for active-source compilation while keeping Msty/Ollama provider degradation acceptable.
- Added text preview exports with `python main.py --preview-theme THEME --export-preview` under `_ARBITER/theme_previews/`.
- Added `python main.py --export-legacy-visuals` for recovered NERV, Arasaka, Janus, CONSENSUS, boot, and loading reference output.
- Recovered large legacy NERV, Arasaka, Janus Security Consortium, and CONSENSUS War Room ASCII logo assets in `static/logos/`.
- Restored legacy theme language for EXCOMM, MAGI, Imperial Gothic, Super Earth, Arasaka counterintelligence, and Janus dual-front identities.
- Restored the default global visual boot flow: NERV tactical BIOS / WAR ROOM INIT first, then Arasaka loading screen labeled `INITIALIZING CONSENSUS WAR ROOM`.
- Added active compile, theme completeness, static asset integrity, and legacy visual identity tests.

## 7.2.0 - Phase 3A Visual Audit and Root Cleanup

- Audited canonical themes: MILITARY, EVA, NERV, WH40K, HELLDIVERS, ARASAKA, and JANUS.
- Expanded theme metadata with canonical aliases, colors, font family, logo asset, boot profile, loading animation, panel/border style, and monolith display labels.
- Added dedicated boot/loading modules and boot profiles for tactical, MAGI/NERV, Imperial cogitator, Super Earth, Arasaka, and JANUS identities.
- Moved ASCII logos into `static/logos/`, including dedicated `static/logos/nerv_logo.txt`.
- Added `main.py --list-themes` and `main.py --preview-theme THEME_NAME`.
- Archived obsolete root files and historical root directories under `archive/` without deletion.
- Added `archive/ARCHIVE_MANIFEST.md` and `tests/test_root_hygiene.py`.

## 7.2.0 - Msty Runtime Layer

- Added `MstyRuntime` with isolated per-agent sessions, streaming facade, provider fallback, and token/latency telemetry hooks.
- Added canonical agent profiles for ARBITER, RATIONALIS, AETERNUM, BELLATOR, and AURELIUS.
- Routed tribunal voting through `VotingOrchestrator -> MstyRuntime -> vote parser -> ConsensusEngine`.
- Added AURELIUS operator scaffolding for Msty Claw style system state, proposal submission, memory query, workflow handoff, and response preparation.
- Added Knowledge Stack interfaces for source registration, source listing, and metadata-only retrieval.
- Added Msty runtime, agent profile, and voting-runtime integration tests.

## 7.1.0 - Modular Coherence Pass

- Split the Genesis runtime into dedicated `core`, `config`, `integrations`, `ui`, and `monoliths` modules.
- Preserved `consensus_war_room_genesis.py` as a compatibility launcher.
- Added canonical agent IDs for ARBITER, RATIONALIS, AETERNUM, BELLATOR, and AURELIUS.
- Added module health checks, unified memory scaffolding, and Msty integration boundaries.
- Added runtime smoke testing for proposal, vote, verdict, and decision-history persistence.
