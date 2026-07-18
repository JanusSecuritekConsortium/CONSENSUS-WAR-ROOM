# Changelog

## 7.15.3 - Provider Preference Test Isolation

- Isolated the dual-runtime provider-preference regression from ambient endpoint variables and model-cache state on GitHub's shared Ubuntu test process.

## 7.15.2 - Cross-Platform CI Test Isolation

- Replaced Windows-only path-string assertions with `pathlib` comparisons so feed, RSS, and validation tests behave consistently on Windows and Linux.
- Limited the Consolas/GDI glyph-coverage check to Windows while preserving all platform-independent logo contracts on GitHub's Ubuntu runner.
- Isolated provider-routing tests from ambient endpoint environment variables and model-cache state, keeping their fake runtime selection deterministic.

## 7.15.1 - GitHub CI Dependency Correction

- Changed GitHub Actions to install the canonical project metadata with the development extra so CI receives Pillow and the supported Flet runtime versions.
- Aligned `requirements.txt` with the packaged Pillow, Flet, and Flet Desktop constraints to prevent local and CI dependency drift.
- Added regression coverage ensuring the CI workflow continues to install `.[dev]` and the legacy requirements file retains the GUI dependencies used by screenshot tests.

## 7.15.0 - Live Boot Hardware Detection

- Added a fresh boot-time hardware snapshot showing usable system RAM, physical CPU cores, and logical CPU threads in every active theme BIOS.
- Replaced the simulated `CO-CPU / 256 SEGMENTS` diagnostic with explicit, human-readable physical-core and logical-thread rows.
- Reused the same live hardware rows in the standalone themed BIOS previews, with clearly marked fallback values when direct topology detection is unavailable.

## 7.14.0 - Dense Interchangeable BIOS Promotion

- Promoted the reviewed dense old-BIOS startup layout into the active console and Flet boot paths for EVA, Arasaka, Military, WH40K, Helldivers, and Janus.
- Preserved each theme's centered boot logo, identity header, author, build, date, provider state, subsystem language, and animated handoff while replacing the former active sequential POST presentation.
- Added a dedicated dark-crimson EVA/NERV boot-logo treatment, darker EVA success blue, and readable high-contrast Arasaka terminal data without changing GUI palette contracts.
- Gave every theme a distinct loading-bar geometry in addition to its existing label, stages, and color.
- Retained the former BIOS line generator for compatibility with archived previews and historical regression contracts; normal startup now uses the dense builder.

## 7.13.40 - EVA GUI Header Source Replacement

- Replaced the dense `56x88` EVA GUI header source with a lower-density `18x39` GUI-specific NERV/MAGI text asset in `static/logos/gui/eva_header.txt`.
- Preserved the EVA `ascii_grid_vector` renderer, `210x162` header region, WH40K, Military, Arasaka, Janus, Helldivers, telemetry, proposal panel, ARBITER, body layout, footer, provider routing, and boot assets.
- Added current-source hash/dimension coverage for all six GUI logo files and updated EVA source-integrity tests for the new canonical asset.

## 7.13.39 - EVA Grid Texture Correction

- Refined the EVA/NERV `ascii_grid_vector` renderer to draw individual occupied source cells instead of solid merged run bands.
- Preserved the canonical EVA GUI text asset, `210x162` region, canvas renderer, telemetry signatures, WH40K, Military, Arasaka, Janus, Helldivers, body layout, proposal panel, ARBITER, and footer.
- Added regression coverage for occupied-cell count, cell fill ratios, containment, and unchanged telemetry signatures.

## 7.13.38 - EVA Vector Grid Logo Renderer

- Replaced only the EVA/NERV header artwork renderer with an `ascii_grid_vector` canvas path that draws merged occupied-cell runs from the unchanged canonical GUI text asset.
- Preserved the EVA source hash, `210x162` logo region, body/proposal/footer geometry, telemetry builders, and all non-EVA logo renderers.
- Added focused regression coverage for exact source handoff, grid dimensions, run merging, containment, no EVA artwork `ft.Text`, no PNG logo assets, and unchanged telemetry signatures.

## 7.13.37 - GUI Logo Source Correction

- Added runtime and bundled-archive regression checks proving EVA and WH40K GUI headers resolve to the canonical `static/logos/gui` text assets and not boot/report/archive sources.
- Reversed WH40K optical correction to a positive `+6px` post-centering offset while preserving the asset, scale, and region dimensions.
- Added one-time logo diagnostics including resolved GUI path, SHA256, and renderer mode for supersampled GUI headers.

## 7.13.36 - Three Logo Correction

- Increased the EVA/NERV supersampled logo region to `210px` so the unchanged artwork clears the right edge without reducing scale.
- Applied the WH40K theme-specific `-3px` optical offset after visible-glyph centring while preserving source, scale, and region size.
- Replaced Military/EXCOMM direct small-font rendering with a `supersampled_banner` renderer using the unchanged GUI asset at base font size `14` inside a `400px` region.

## 7.13.35 - Narrow Header Corrections

- Compacted EVA/MAGI header telemetry by keeping the three vertical MAGI channels and replacing lower thermal gauges with a compact horizontal thermal row.
- Preserved WH40K source/scale while adding visible-glyph centring regression coverage for the supersampled renderer.
- Reduced the Military/EXCOMM header logo region to `430px`, scaled the historical text artwork into the requested bounds, and disabled header-logo scrolling.

## 7.13.34 - Distinct Header Telemetry and Logo Geometry

- Rebuilt themed header telemetry into six distinct Flet-native layouts with structural regression coverage and per-theme layout diagnostics.
- Added canonical CPU/GPU temperature fields, guarded Windows sensor collection, bounded thermal histories, and thermal status display without synthetic readings.
- Corrected theme-specific header logo geometry for Janus, Helldivers, Arasaka, EVA/MAGI, WH40K, and Military while preserving raw logo assets and frozen body/proposal/footer geometry.

## 7.13.33 - Themed Header Telemetry Visuals

- Added a dedicated `ui/components/telemetry_widgets.py` module for themed Flet-native header telemetry controls.
- Replaced the header's plain text-only telemetry list with per-theme segmented meters, compact history indicators, and preserved numeric metric labels.
- Bounded telemetry history defaults to 30 samples with a minimum 1-second sampling interval, while preserving provider routing, logos, body layout, proposal, footer, and ARBITER geometry.

## 7.13.32 - GUI Logo Semantic Asset Rollback

- Restored the canonical EVA/MAGI and WH40K GUI header assets from the archived v7.13.30 GUI sources, removing boot-sequence assets from GUI headers.
- Added GUI logo path validation so production header assets must resolve beneath `static/logos/gui`.
- Added boot-hash denylist regression coverage for EVA/MAGI and WH40K while preserving the supersampled square renderer and frozen layout geometry.

## 7.13.31 - Selected GUI Logo Asset Replacement

- Replaced the canonical EVA/MAGI GUI logo with the selected `nerv_logo.txt` candidate and the canonical WH40K GUI logo with the selected `cogitator_logo.txt` candidate.
- Archived the outgoing v7.13.30 dense EVA and WH40K GUI assets under `reports/logo_history_candidates`.
- Preserved the v7.13.30 `supersampled_square` renderer, fixed `162x162` logo cells, and frozen body/proposal/footer/provider behavior.

## 7.13.30 - Supersampled Dense Logo Renderer

- Replaced the EVA/MAGI and WH40K tiny-font square logo path with a supersampled ASCII text renderer that lays out the full source at integer base font size `10` and uniformly fits the natural canvas into the `162x162` viewport.
- Preserved the current EVA, WH40K, and Military source assets byte-for-byte and kept dense logos text-based with no PNG/raster asset generation.
- Added regression coverage for source hashes, integer base font size, fit-scale containment, no wrapping/ellipsis, fixed square cells, and frozen body/proposal/footer geometry.

## 7.13.29 - Square Logo Scale-Up Correction

- Increased EVA/MAGI and WH40K square-cell visual scale while preserving raw assets, font sizes, and `162x162` cells.
- Kept WH40K at the smallest allowed adjusted scale that satisfies the deterministic `5px` clearance invariant.
- Preserved Military, Arasaka, Janus, Helldivers, ARBITER, proposal, body layout, footer, provider routing, and boot behavior.

## 7.13.28 - Explicit Square Logo Scale Transform

- Applied a centered uniform visual scale transform to EVA/MAGI and WH40K square-cell logo text while preserving raw assets, `162x162` cells, and frozen font sizes.
- Added deterministic transform bounds checks for occupancy, clearance, centered uniform scaling, and unchanged square-cell geometry.
- Preserved Military, Arasaka, Janus, Helldivers, ARBITER, proposal, body layout, footer, provider routing, and boot behavior.

## 7.13.27 - Square Logo Breathing Room Adjustment

- Reduced EVA/MAGI and WH40K square-cell render scale only, preserving the `162x162` cells and raw text assets.
- Updated square-cell bounds checks to use visible ASCII bounds and require target occupancy plus at least `8px` clearance.
- Kept Military, Arasaka, Janus, Helldivers, ARBITER, proposal, body layout, footer, and provider routing unchanged.

## 7.13.26 - Final Square Logo Scale Correction

- Increased EVA/MAGI and WH40K square-cell render scale without changing square-cell dimensions, raw logo assets, or header geometry.
- Preserved Military, Arasaka, Janus, Helldivers, ARBITER, proposal, body, footer, and provider routing.
- Tightened square-cell regression checks to require `0.91-0.94` visible-height occupancy with at least `3px` deterministic clearance.

## 7.13.25 - Square Logo Cells and EXCOMM Renderer Recovery

- Added explicit header logo layout modes: percentage, square, and historical.
- Moved EVA/MAGI and WH40K out of percentage splits into square logo cells derived from the fixed header logo height.
- Preserved WH40K source bytes and adjusted no other accepted theme assets.
- Restored Military/EXCOMM to the recovered `f7248fc` text renderer settings with the historical fixed logo box and font sizing.
- Added containment, glyph-coverage, renderer provenance, and frozen geometry tests while preserving ARBITER, proposal, body, footer, and provider routing.

## 7.13.24 - Narrow Logo and Verdict Bounds Correction

- Restored the larger historical EVA/MAGI and Military/EXCOMM GUI text assets without rasterizing or normalizing them.
- Added EVA and Military theme-specific header splits while leaving Janus, Helldivers, and Arasaka rendering unchanged.
- Reduced WH40K logo render scale only; the accepted WH40K asset and split remain unchanged.
- Compacted ARBITER verdict internals so context and reasoning lines clear the fixed footer at review viewports.
- Preserved `25 / 54 / 21` body layout, `PROPOSAL_HEIGHT = 270`, `FOOTER_HEIGHT = 58`, proposal internals, monolith cards, and provider routing.

## 7.13.23 - Historical Header Logo Restoration

- Restored EVA/MAGI, WH40K, and Military/EXCOMM GUI logo text assets directly from selected historical commits.
- Kept Arasaka source unchanged and restored its earliest working text-render settings.
- Added theme-aware header splits with default `23 / 77`, Arasaka `34 / 66`, and WH40K `28 / 72`.
- Preserved frozen body layout `25 / 54 / 21`, `PROPOSAL_HEIGHT = 270`, and `FOOTER_HEIGHT = 58`.
- Added regression coverage for historical asset byte integrity, text-based logo rendering, theme-specific header splits, and absence of GUI PNG logo assets.

## Documentation - Canonical MstyConsensusLauncher v1.1.3

- Updated canonical launcher documentation from `MstyConsensusLauncher v1.1.2` to `v1.1.3`.
- Recorded `msty_window_mode` with default `minimized` behavior.
- Documented `hidden` mode as best-effort and `MSTY_WINDOW_HANDLE_NOT_FOUND` as non-fatal.
- Clarified that Start Menu shortcut metadata may be warning-only without elevation, while the Windows Startup shortcut remains a critical self-test requirement.
- No CONSENSUS or launcher version bump; documentation-only update.

## 7.13.19 - CONSENSUS Launcher Environment Routing

- Bumped CONSENSUS to v7.13.19.
- Updated Msty provider routing to consume launcher-injected `CONSENSUS_MSTY_BASE_URL` first, then `MSTY_BASE_URL`, then configured/default endpoints.
- Confirmed AURELIUS provider routing uses `AURELIUS_MSTY_BASE_URL`, then `MSTY_BASE_URL`, then default degraded behavior when no endpoint is configured.
- Added provider diagnostics fields for selected backend, selected endpoint, and normalized endpoint source (`env`, `config`, or `default`).
- Added regression coverage for CONSENSUS and AURELIUS environment override behavior.

## 7.13.18 - Msty Consensus Launcher Operator Hardening

- Added read-only `--print-config` / `--print-config --json` to print the effective launcher config after default application without probing APIs or touching shortcuts.
- Added redaction for sensitive environment variable names before logging or status/config JSON output.
- Added `G:\Tools\MstyConsensusLauncher\regression-test.ps1` for read-only command checks and temporary malformed-config validation.
- Added versioned EXE backup packaging for the current launcher build.

## 7.13.17 - Msty Consensus Launcher CONSENSUS Environment Injection

- Bumped `MstyConsensusLauncher` to v1.1.2 with child-process-only environment injection for the selected semantically-ready Msty API endpoint.
- Added `consensus_environment_variables` and `enable_consensus_environment_injection` config fields, with `{selected_msty_api_url}` replacement at launch time.
- Added `CONSENSUS_ENV_INJECT_STARTED`, `CONSENSUS_ENV_SET`, `CONSENSUS_ENV_INJECT_COMPLETE`, `CONSENSUS_ENV_INJECT_DISABLED`, and `CONSENSUS_LAUNCH_ENDPOINT` logging.
- Extended `--status` / `--status --json` with CONSENSUS launch endpoint, environment injection state, and configured environment variable templates.
- Extended `--self-test` with critical validation for malformed environment variable configuration and warning behavior for an empty environment map.

## 7.13.16 - Msty Consensus Launcher Fallback API Selection

- Bumped `MstyConsensusLauncher` to v1.1.1 with fallback Msty API endpoint support controlled by `fallback_msty_api_urls` and `allow_fallback_api`.
- Added semantic endpoint selection order: primary `msty_api_url` first, then configured fallbacks, selecting the first `/v1/models` endpoint with HTTP 200, valid JSON, a `data` array, and at least one model.
- Extended `--diagnose-api` to show primary and fallback probe results plus the selected endpoint.
- Extended `--status` / `--status --json` with selected API endpoint, fallback enablement, fallback URLs, and fallback probe results.
- Extended `--self-test` with fallback URL syntax validation, warning when fallback is disabled and critical failure when fallback is enabled.

## 7.13.15 - Msty Consensus Launcher API Model Readiness

- Bumped `MstyConsensusLauncher` to v1.1.0 with `--diagnose-api` for read-only diagnostics against `<msty_api_url>/v1/models`.
- Changed launch readiness to require HTTP 200, valid JSON, a `data` array, and at least one detected model before launching CONSENSUS.
- Extended `--status` / `--status --json` with the models endpoint, semantic API readiness, model count, and model IDs.
- Extended `--self-test` so API down or empty model state remains a warning while config, path, and shortcut checks remain critical.

## 7.13.14 - Msty Consensus Launcher Port Diagnostics

- Bumped `MstyConsensusLauncher` to v1.0.9 with `--diagnose-port` for read-only Msty API port ownership diagnostics.
- Added configured API URL parsing, API readiness reporting, TCP listener detection, listener PID/process/path output, and logging for `PORT_OCCUPIED_API_NOT_READY` and `PORT_NOT_LISTENING`.
- Extended `--status` / `--status --json` with Msty API host/port and port listener ownership fields.
- Extended `--self-test` with a warning when the configured Msty API port is occupied while the API is not ready.

## 7.13.13 - Msty Consensus Launcher Shortcut Repair

- Bumped `MstyConsensusLauncher` to v1.0.8 with `--install-shortcuts` for creating or repairing the Windows Startup shortcut and the user Start Menu shortcut.
- Added shortcut install logging for `SHORTCUT_INSTALL_STARTED`, `SHORTCUT_CREATED`, `SHORTCUT_REPAIRED`, `SHORTCUT_ALREADY_VALID`, and `SHORTCUT_INSTALL_COMPLETE`.
- Hardened `--self-test` to validate shortcut target path, arguments, and working directory instead of checking existence only.
- Updated `--status` / `--status --json` to report shortcut states as `VALID`, `INVALID`, or `MISSING`, and added shortcut paths to JSON output.

## 7.13.12 - Msty Consensus Launcher Mutex and Log Rotation

- Bumped `MstyConsensusLauncher` to v1.0.7 with a named Windows mutex, `Global\MstyConsensusLauncher`, so only one launcher instance can execute launch, recovery, startup, status, self-test, open-logs, or tail-log logic at a time.
- Added `INSTANCE_ALREADY_RUNNING` handling with a clear operator message and exit code `0` when another launcher instance already owns the mutex.
- Added launcher log rotation controlled by `log_retention_days` and `max_log_files`, deleting only `msty-consensus-launcher-*.log` files and logging `LOG_ROTATION_STARTED`, `LOG_ROTATION_DELETED`, and `LOG_ROTATION_COMPLETE`.
- Extended `--status` / `--status --json` with single-instance lock and log-retention fields, and extended `--self-test` with mutex and log-rotation config validation.

## 7.13.11 - Msty Consensus Launcher External Config

- Bumped `MstyConsensusLauncher` to v1.0.6 with external JSON configuration at `G:\Tools\MstyConsensusLauncher\launcher.config.json`.
- Added automatic default config creation, config loading, malformed-config detection with `CONFIG_INVALID`, and missing-field default fallback logging with `CONFIG_DEFAULT_USED`.
- Routed Msty API URL, CONSENSUS executable path, log directory, startup delay, stale recovery timeout, stale relaunch delay, known Msty process names, and stale recovery enablement through config while preserving default runtime behavior when no config exists.
- Extended `--self-test` to validate config and `--status` / `--status --json` to report config path and validity.

## 7.13.10 - Msty Consensus Launcher Maintenance Commands

- Bumped `MstyConsensusLauncher` to v1.0.5 with read-only maintenance commands for operator upkeep.
- Added `--open-logs` to open `G:\Msty\logs` in Windows Explorer without launching Msty, launching CONSENSUS, or terminating processes.
- Added `--tail-log` to print the last 80 lines of the latest launcher log with exit codes `0` for log found, `1` for no log found, and `2` for unexpected exceptions.
- Added `--help` output listing all supported flags: `--startup`, `--no-recover`, `--self-test`, `--status`, `--status --json`, `--open-logs`, `--tail-log`, and `--help`.

## 7.13.9 - Msty Consensus Launcher Status Mode

- Bumped `MstyConsensusLauncher` to v1.0.4 with a read-only `--status` mode for compact operator-facing runtime status.
- Added `--status --json` for machine-readable status output covering launcher version, Msty API readiness, known Msty process state, CONSENSUS process state, Startup shortcut, Start Menu shortcut, and last log path.
- Kept `--status` non-invasive: it does not launch Msty, terminate processes, or launch CONSENSUS, and returns `0` for operational or partially operational states, `1` for critical path failures, and `2` for unexpected exceptions.

## 7.13.8 - Msty Consensus Launcher Self-Test

- Bumped `MstyConsensusLauncher` to v1.0.3 with a read-only `--self-test` mode that does not launch Msty, terminate processes, or launch CONSENSUS.
- Added PASS/WARN/FAIL checks for launcher version, Msty endpoint configuration, port `11964` readiness, known Msty/MstyClaw processes, `CONSENSUS.exe` presence/running state, log directory presence, Startup shortcut `--startup`, and Start Menu pinning shortcut presence.
- Added self-test result logging under `G:\Msty\logs` with exit code `0` for critical pass, `1` for critical failures, and `2` for unexpected exceptions.

## 7.13.7 - Msty Consensus Launcher Stale Recovery

- Bumped `MstyConsensusLauncher` to v1.0.2 with stale-Msty recovery for cases where known Msty/MstyClaw processes are running but `http://127.0.0.1:11964` never becomes ready.
- Added `STALE_MSTY_DETECTED` logging, allowlisted Msty/MstyClaw process termination, a randomized 3-5 second recovery pause, Msty relaunch, and a second readiness wait before launching CONSENSUS.
- Added `--no-recover` to disable process termination while still logging stale-state detection and preventing CONSENSUS launch until Msty readiness is restored.

## 7.13.6 - Msty Consensus Launcher Duplicate Protection

- Added `MstyConsensusLauncher` v1.0.1 with explicit startup-stage logging under `G:\Msty\logs`.
- Prevented duplicate Msty startup when a known Msty process is already running or the Msty Local AI API at `http://127.0.0.1:11964` is already ready.
- Prevented duplicate `G:\CONSENSUS_SYSTEM\dist\CONSENSUS.exe` launches by checking the running executable path before starting CONSENSUS.
- Confirmed the Windows Startup shortcut uses `--startup` for randomized boot-delay launch behavior while the launcher starts child processes detached and exits without terminating Msty services.

## 7.13.5 - CONSENSUS MCP AURELIUS Path Fix

- Fixed CONSENSUS MCP AURELIUS path resolution to use `G:\CONSENSUS_SYSTEM\_ARBITER\Bot` from `PROJECT_ROOT` instead of the obsolete external `G:\CONSENSUS_SYSTEM_ARBITER\Bot` path.
- Restored `consensus_status` key-file detection for `aurelius_bot.py` and `aurelius_launcher.bat`.
- Added MCP regression coverage for the corrected AURELIUS root and launcher/bot file presence.

## 7.13.4 - CONSENSUS MCP Server for MstyClaw

- Added local CONSENSUS MCP server for MstyClaw integration with read-only status, logs, model discovery, project tree, safe file read, and text search tools.
- Added `integrations/mcp/run_consensus_mcp.bat` and MCP registration documentation for local command transport.
- Added MCP self-test coverage for path traversal rejection, `.env` redaction, Msty health/model discovery shape, AURELIUS log reads, and project tree exclusions.

## 7.13.3 - Theme-Safe UI Scaling Pass

- v7.13.3: Theme-safe UI scaling pass. Enlarged proposal panel, fixed telemetry/header clipping, added bounded logo profiles, and protected long system-status strings.
- Separated GUI header logo registry from boot-logo assets so the WAR ROOM header uses only `static/logos/gui/*` while BIOS/startup keeps `static/logos/*`.
- Added explicit full/compact/micro GUI header fallback handling without arbitrary ASCII cropping.
- Tightened ARBITER voice dispatch reporting so generated audio without confirmed playback is logged as degraded instead of successful.
- Separated normal operator boot from release validation: `boot.bat` launches quickly, `--safe` runs diagnostics only, `--validate` runs tests/compile/screenshots, and `--test-theme` runs targeted theme/layout checks.

## 7.13.2 - AURELIUS Telegram Cleanup

- Retired the active legacy ANIMA Telegram bootstrap and archived it under `archive/legacy_bots/anima_bot.py`.
- Added the clean `_ARBITER/Bot/aurelius_bot.py` entrypoint with Msty-only provider routing through `integrations/msty/aurelius_provider.py`.
- Preserved the 08:00 Morning Brief and 18:00 End-of-Day Shutdown schedules while suppressing repeated scheduled Telegram errors when Msty is missing or unavailable.
- Removed direct IBKR imports from Telegram startup, refreshed launch files, and declared the active Telegram dependencies without `ib_insync`.

## 7.13.1 - RSS Intelligence Backbone

- Added the RSS-first Bellator intelligence backbone with a local SQLite FTS5 cache at `_ARBITER/cache/data_sources/intelligence.db`, configurable 20-minute polling, conditional HTTP requests, per-source backoff, and explicit feed health states.
- Added strict RSS/Atom probe tooling with official-directory discovery, XML structure validation, content-type checks, and redirect-to-HTML detection. Reuters and AP remain quarantined until valid current XML endpoints are confirmed.
- Added GUID, canonical-URL, and stable-content-hash deduplication plus bounded Bellator retrieval packets with taxonomy filtering, freshness weighting, citations, and marked `CACHE_FALLBACK` behavior.
- Registered Tier 1 institutional and Tier 2 editorial/OSINT feeds, kept Tier 3 APIs as enrichment only, and added RSS health/sample artifacts to runtime snapshots and bundles.
- Added offline regression coverage for probing, conditional headers, FTS retrieval, deduplication, backoff, quarantine, bounded packet construction, and cache fallback.

## 7.13.0 - Real Data Layer Foundation

- Added a normalized, environment-configured data-source registry with TTL cache fallback, freshness reporting, source health, and secret redaction.
- Added guarded ACLED, GDELT, Factal, Ground News, IBKR, public RSS, and configured-search adapters. Credentialed sources remain disabled by default, Ground News scraping is prohibited, and IBKR is read-only.
- Added cache-only BELLATOR and AETERNUM enrichment packets with explicit unavailable states and anti-fabrication instructions for tribunal prompts.
- Added data-source health and feed overlays to the command palette, runtime snapshot observability, and redacted runtime bundle artifacts.
- Bundled the source configuration for frozen executable builds and documented optional source environment variables.

## 7.12.1 - Standalone Operator Executable

- Added the PyInstaller build pipeline (`build_exe.py`, `build_exe.bat`, and `CONSENSUS.spec`) for a one-file `dist/CONSENSUS.exe` operator build.
- Routed frozen static resources through the PyInstaller extraction root while preserving writable runtime state beside the executable.
- Bundled theme assets, ASCII logos, icon assets, tracked genesis configuration, and voice profile configuration.
- Added Windows executable metadata for CONSENSUS SYSTEM by Janus Securitek Consortium.
- Added frozen asset, executable boot entrypoint, and PyInstaller specification regression coverage.

## 7.12.0 - Simulation Workflow

- Activated the deterministic operator-driven simulation workflow with create, history, branch-tree, branch expansion, and dossier export overlays.
- Added Markdown and JSON simulation dossier exports plus runtime snapshot and runtime bundle simulation integration.
- Added canonical `boot.bat` and `boot.ps1` operator launchers with dependency/provider checks, random or configured startup theme selection, BIOS/POST transition, GUI startup, and diagnostics-only safe mode.
- Restored the SESSION header row across every theme and raised the top-right status/telemetry content slightly without changing theme assets, colors, or lower-right diagnostics layout.

## 7.11.13 - ARBITER Verdict Voice Dispatch

- Added a dedicated ARBITER/GLaDOS verdict voice dispatcher for every terminal tribunal outcome, including NO_CONSENSUS and classification failure.
- Routed GUI terminal verdict announcements through the ARBITER voice path instead of the AURELIUS operator voice path.
- Added once-per-proposal dispatch guards, non-blocking GUI dispatch, and success/failure/degraded voice logging.
- Added runtime snapshot and diagnostics voice status with the latest voice announcement metadata.
- Added a manual ARBITER voice test script for terminal verdict announcements.

## 7.11.12 - Telemetry Relocation and Diagnostics Freeze Fix

- Moved live telemetry into the top-right header system area with compact theme-specific summary lines and widened text graphs.
- Converted the lower-right telemetry slot into the health/system diagnostics summary area while preserving provider, active model, memory, context, and lifecycle visibility.
- Made diagnostics drawer toggling use cached GUI snapshot state and avoid fresh runtime snapshot work on the UI thread.
- Added overlay replacement/reentrant regression coverage so repeated diagnostics opens do not stack drawers or freeze the interface.

## 7.11.11 - WAR ROOM Layout Consistency Refinement

- Tightened WH40K, EVA/NERV, HELLDIVERS, and ARASAKA header logo containers through theme metadata without changing ASCII assets or color palettes.
- Expanded right-column telemetry presentation by stretching the panel across available width and widening theme-specific text graphs.
- Removed the Helldivers header `SESSION` status row for consistency with the other system status presentations.
- Improved ARASAKA proposal template dropdown contrast with black/red option styling while preserving the existing proposal title and theme palette.
- Reordered displayed and registered tribunal monoliths to `BELLATOR`, `AETERNUM`, `RATIONALIS`, then `ARBITER`, and enforced an explicit console boot gap after the ARASAKA logo.

## 7.11.10 - Editable Install Packaging Fix

- Added explicit setuptools package discovery for active Python packages so `python -m pip install -e .` no longer treats archive, reports, static assets, or future implementation roots as installable packages.
- Preserved `psutil`, `requests`, `flet`, and `flet-desktop` runtime dependencies from the v7.11.9 GUI launch fix, with Flet constrained to the supported `0.28.x` desktop API line.
- Declared Pillow for the existing theme gallery/logo verification path so venv-based release verification does not depend on globally installed packages.
- Added regression coverage for editable-install package discovery metadata.

## 7.11.9 - Flet Desktop Runtime Dependency Fix

- Declared `flet`, `flet-desktop`, and `requests` as runtime dependencies so editable installs provision the desktop GUI runtime instead of relying on Flet auto-install behavior.
- Added a GUI launch preflight that checks for the importable `flet_desktop` module and raises a clear install command before opening the WAR ROOM.
- Updated dependency diagnostics to include `flet_desktop` as a required runtime dependency.

## 7.11.8 - User ASCII Header Assets

- Replaced the EVA/NERV and HELLDIVERS GUI header ASCII assets with the user-provided final framebuffer text files as canonical sources.
- Preserved exact asset bytes for the new headers, including leading spaces, trailing spaces, and line breaks, and updated header rendering to use non-wrapping non-selectable monospace text.
- Updated theme header metadata so the taller EVA framebuffer and HELLDIVERS emblem fit their header boxes without changing theme colors or WAR ROOM body proportions.
- Added regression coverage rejecting the previous generated EVA/HELLDIVERS caption tokens and enforcing byte-level asset hashes, whitespace preservation, and no-wrap rendering.

## 7.11.7 - AURELIUS Msty Provider Migration

- Removed AURELIUS Telegram bot dependency on direct Ollama endpoints and moved provider resolution to a central Msty-only resolver.
- Added environment-driven AURELIUS Msty endpoint configuration with fallback disabled by default and clear degraded messaging when the endpoint is not configured.
- Updated scheduled Morning Brief and End-of-Day Shutdown jobs to log provider configuration failures once and avoid repeated Telegram error spam.
- Updated active AURELIUS config defaults to Msty and removed active port 11434 endpoint configuration from the Telegram/CONSENSUS workflow.

## 7.11.6 - WAR ROOM UI Correction

- Tightened the Arbiter Verdict panel with fixed padding, fixed section spacing, bounded timeline/vector/reasoning regions, synthesis line limits, and hard clipping to prevent overlap or floating controls.
- Removed the visible Aurelius voice-loop switch from the footer command bar so Diagnostics remains visible in the right-side auxiliary control region.
- Replaced the EVA/NERV GUI header with a NERV-reference-derived ASCII mark and replaced the HELLDIVERS header with a tighter skull/wings ASCII mark based on the provided emblem reference.
- Tightened WH40K header presentation by reducing the WH40K-only logo box width while preserving the restored v7.10.13 gothic ASCII asset and colors.
- Enforced exactly one deterministic blank line between the ARASAKA logo and `ARASAKA EXECUTIVE SECURITY BIOS...` boot text.
- Added regression coverage for footer diagnostics visibility, absence of footer controls in the Arbiter panel, bounded verdict panel sections, reference-derived ASCII headers, and exact BIOS spacing.

## 7.11.5 - Active Tribunal Flow

- Added explicit tribunal processing phases from `IDLE` through classification, dispatch, analysis, deliberation, synthesis, terminal outcome, and export-ready state.
- Added bounded tribunal phase events, phase duration tracking, convergence percentage, and status-only reasoning stream metadata to runtime logs, decision traces, runtime snapshots, and GUI state.
- Expanded the Arbiter Verdict panel with a phase timeline, convergence meter, and compact active reasoning-state stream without exposing hidden reasoning.
- Restored the WH40K header to the v7.10.13 gothic ASCII asset and made it fit through WH40K-only header metadata rather than global layout changes.
- Replaced the EVA/MAGI GUI header with a blocky rectangular MAGI cube-style ASCII asset and tightened Super Earth ASCII header symmetry while preserving all theme colors.
- Preserved telemetry no-scroll behavior, WAR ROOM 2:6:2 structure, canonical ASCII rendering, Msty local defaults, and screenshot-loop constraints.
- Added regression coverage for tribunal lifecycle ordering, convergence visualization, bounded reasoning stream history, lifecycle runtime snapshots, WH40K full visibility, and updated header identity contracts.

## 7.11.4 - WAR ROOM Layout Correction

- Rebalanced GUI header metadata and replaced the WH40K, HELLDIVERS, and EVA compact ASCII headers with fit-safe tactical text assets that remain fully visible in the fixed WAR ROOM header.
- Centered footer shortcut guidance between fixed left theme selection and right operator controls without changing the 2:6:2 body layout.
- Increased proposal-to-verdict spacing, normalized proposal panel padding, and reduced proposal input height to prevent visual collision with the Arbiter Verdict panel.
- Redesigned telemetry into fixed-height, no-scroll text metrics with compact bars and theme-specific telemetry style labels for all core CPU/RAM/DISK/GPU/VRAM/TEMP values.
- Added layout metadata for proposal spacing, telemetry height, footer alignment, and WH40K-specific compaction permissions.
- Added regression coverage for WH40K visibility, footer centering, proposal/verdict separation, telemetry visibility, and EVA/HELLDIVERS ASCII quality.

## 7.11.3 - Randomized BIOS Boot Phrase System

- Added modular boot phrase registries under `ui.boot` for rotating device detection, POST checks, cosmetic sync/warn states, and monolith initialization phrases.
- Adapted legacy CLAUDSENSUS/NERV boot material into active BIOS atmosphere without modifying archive roots or pasting legacy boot code into UI startup.
- Expanded theme-aware boot vocabulary for MAGI/NERV, ARASAKA, EXCOMM/MILITARY, WH40K, HELLDIVERS/Super Earth, and JANUS while preserving the stable boot structure.
- Added deterministic fallback and seeded randomization support so tests remain reproducible while live boots avoid repetitive device/POST/tribunal sequences.
- Added regression coverage for boot phrase registry completeness, randomization, theme vocabulary selection, structured boot output, and duplicate-line prevention.

## 7.11.2 - Application Icon Identity

- Added dedicated CONSENSUS War Room application icon assets in PNG and ICO formats using a compact tribunal triad and central verdict-node mark.
- Wired the Flet desktop window icon through a guarded app-icon resolver with fallback behavior when icon assets are unavailable.
- Added app icon validation coverage for asset presence, readable/non-empty files, configured Flet window usage, and replacement of the old default arrow-style icon.
- Preserved theme logos, theme colors, WAR ROOM 2:6:2 layout, Msty local defaults, and screenshot-loop constraints.

## 7.11.1 - WAR ROOM Visual Refinement Pass

- Refined header logo layout metadata with deterministic box widths, centered alignment, balanced padding, and fixed header constraints across all GUI themes.
- Replaced the HELLDIVERS GUI header with a sparse ASCII Super Earth-style emblem while preserving the text-only terminal identity system and existing color palette.
- Increased WH40K header readability through metadata sizing without changing its canonical gothic ASCII asset.
- Constrained telemetry panel height and line flow so telemetry cannot collide with lower UI boundaries.
- Tightened proposal panel spacing and padding while preserving template and lifecycle behavior.
- Added visual structure regression coverage for header alignment, header constraints, telemetry containment, proposal spacing, HELLDIVERS logo quality, theme consistency, and vertical logo budget.

## 7.11.0 - Simulation Layer Foundation

- Added deterministic simulation architecture under `core.simulation` with scenario models, branch models, registry definitions, branch probability/risk scaffolding, and JSONL simulation history.
- Added command palette actions and overlay plumbing for creating and viewing simulation scaffolds without mutating the WAR ROOM 2:6:2 layout.
- Added simulation status to runtime snapshots and runtime bundles.
- Improved ARASAKA SYSTEM STATUS readability by using readable secondary text for low-emphasis header labels while preserving the black/red aesthetic and accent red.
- Added architecture regression coverage for simulation models, branch generation/scoring, simulation store/registry, GUI simulation actions, runtime snapshot simulation status, and ARASAKA readability.

## 7.10.17 - Proposal Verdict Lifecycle

- Linked proposal records to finalized decision traces with append-only JSONL revisions, terminal decision status, decision timestamps, and linked verdict export paths.
- Added proposal lifecycle helpers for trace linking, status transitions, verdict export attachment, and proposal decision summaries.
- Added dossier export tooling for combined proposal and verdict briefing packages in Markdown and JSON.
- Enhanced the Proposal History overlay with decision-status badges, linked-verdict availability, Open Verdict, Export Dossier, and Reopen Draft actions without changing the 2:6:2 WAR ROOM layout.
- Added proposal lifecycle counts and latest dossier export metadata to runtime snapshots and runtime bundles.
- Added regression coverage for automatic linking, corrupt JSONL tolerance, status mapping, dossier exports, GUI verdict status, reopen-as-draft immutability, lifecycle counts, and bundle dossier artifacts.

## 7.10.16 - Proposal Lifecycle UX

- Added canonical proposal templates for geopolitical, market/finance, technical, operational-risk, and general tribunal queries with validation and non-mutating rendering helpers.
- Added JSONL proposal history storage with corrupt-line tolerance, draft/submitted/resubmitted/archive lifecycle states, resend, duplicate/edit, and archive operations.
- Added proposal template selection and proposal history overlays to the WAR ROOM operator flow while preserving the 2:6:2 body layout and existing theme colors/logos.
- Added latest verdict export to Markdown and JSON, plus command-palette and diagnostics access for proposal history and verdict export status.
- Integrated proposal history and latest verdict exports into runtime snapshots and runtime bundles.
- Added compact footer shortcut guidance for Ctrl+K, Ctrl+D, Ctrl+T, Ctrl+H, and Ctrl+E without changing the footer contract.
- Added regression coverage for proposal templates, rendering, history storage, resend/duplicate/archive behavior, verdict exports, GUI empty states, footer shortcuts, runtime snapshots, and runtime bundles.

## 7.10.14 - Manual Header Refinement

- Moved theme-specific GUI logo/header placement into `ui.assets.registry` as explicit header layout metadata for font size, top/bottom padding, alignment, and scroll behavior.
- Replaced only the WH40K GUI header asset with a compact cogitator/eagle mark that preserves canonical WH40K tokens while fitting the header box at readable size.
- Reverted the rejected WH40K compact skull/cogitator mark back to the v7.10.13 gothic ASCII header after manual review.
- Adjusted ARASAKA, HELLDIVERS/Super Earth, MILITARY, and JANUS header presentation through layout metadata only; canonical non-WH40K assets and all theme colors remain unchanged.
- Preserved extra ARASAKA boot spacing between the logo block and the executive security BIOS text.
- Added regression coverage for header layout metadata, WH40K compact asset dimensions/tokens, boot logo spacing, header vertical offsets, and unchanged theme colors.
- Kept screenshot automation disabled for this review path and marked affected themes for manual visual review.

## 7.10.13 - Slow-Budget Cleanup and Header Presentation

- Isolated Msty runtime provider tests from live backend latency by mocking provider health/send paths while preserving provider-branch runtime coverage under PROVIDER and ALL test runs.
- Added a FAST-only Msty mock runtime path and runner category safeguards so routine FAST verification excludes live/provider-heavy runtime checks.
- Reworked the hidden GUI launch smoke path to render a deterministic WAR ROOM state inside a real hidden Flet app and return immediately after readiness is confirmed.
- Added readiness regression coverage for the GUI smoke marker and provider category selection.
- Adjusted header logo presentation only: ARASAKA and JANUS are centered/lowered in the header box, tall WH40K/Super Earth/MILITARY headers use theme-specific font sizing, and ARASAKA boot output has clearer separation between logo and BIOS text.
- Preserved canonical logo asset contents, WAR ROOM 2:6:2 body layout, screenshot-loop constraints, JANUS asset content, Msty local defaults, and integrity tooling.

## 7.10.12 - GUI Heavy-Test Optimization

- Added a shared GUI/Flet test harness that builds deterministic `GuiState` fixtures without live provider, telemetry, memory, or runtime refresh work.
- Refactored the heaviest GUI regression tests to inspect components and window-mode behavior through the harness while preserving checks for compact header logos, window modes, canonical logo rendering, and the 2:6:2 body layout contract.
- Added harness regression coverage so future GUI tests can reuse the fast state setup without weakening overlay or layout assertions.
- Extended verification manifests with optional before/after duration comparison data when a previous manifest is available.
- Preserved canonical ASCII assets, JANUS visuals, Msty local defaults, integrity tooling, and the manual-screenshot review workflow.

## 7.10.11 - Verification Runtime Optimization

- Added category-aware script test execution to `tools/run_tests.py` with FAST, GUI, SLOW, PROVIDER, and INTEGRATION filters.
- Added `--fast`, `--gui`, `--slow`, `--provider`, `--integration`, `--all`, `--list`, and `--json` runner modes while preserving full-suite default behavior.
- Added duration reporting with slowest-test output, slow-test budget warnings, strict budget mode, and GUI launch-heavy test reporting.
- Extended verification manifests and runtime bundles with duration report data for follow-up test consolidation work.
- Added regression tests for category selection, duration reports, budget warnings, and verification manifest duration fields.

## 7.10.10 - Telemetry Dependency Hardening

- Added `tools/check_dependencies.py` for JSON and human-readable dependency diagnostics across required runtime modules and optional GPU telemetry backends.
- Made telemetry psutil failures explicit with `DEGRADED` status, `psutil missing` degraded reason, and install hints for local remediation.
- Updated GUI telemetry text to show CPU/RAM/DISK unavailable states and degraded reasons instead of silent blanks.
- Added dependency status to runtime snapshots and runtime bundles, including required/optional dependency availability.
- Added regression coverage for dependency checks, psutil-missing telemetry degradation, runtime snapshot dependencies, and GUI degraded telemetry messaging.

## 7.10.9 - Manual Visual Review and Telemetry Layer

- Added a manual visual review registry and `tools/record_visual_review.py` so operator-provided screenshots can be tracked without restarting screenshot automation loops.
- Added diagnostics and command palette access for visual review status, including pending and needs-fix/rejected counts, while preserving the WAR ROOM 2:6:2 body layout.
- Added failure-safe system telemetry collection for CPU, RAM, disk, and optional GPU/VRAM/temperature data with bounded 60-sample history.
- Added a theme-specific telemetry panel and command palette telemetry snapshot overlay with text-readable metrics and lightweight sparklines.
- Included manual visual review and telemetry summaries in runtime snapshots and runtime export bundles.
- Added regression coverage for manual review registry updates, telemetry collection/history/no-GPU behavior, GUI telemetry, GUI visual review status, and runtime snapshot telemetry.

## 7.10.8 - Canonical Theme Identity Stabilization

- Added canonical token and dimension enforcement for every active WAR ROOM header logo asset.
- Preserved canonical ARASAKA and EXCOMM/MILITARY full ASCII assets while extending validation to EVA/NERV, WH40K, HELLDIVERS, and JANUS.
- Forced active GUI logo rendering through a single fixed-width `Consolas` family with explicit no-wrap text styling to prevent crooked ASCII fallback rendering.
- Replaced interim WH40K and HELLDIVERS banners with the user-provided canonical gothic/eagle and Super Earth skull-style ASCII assets; JANUS was left unchanged.
- Preserved the WAR ROOM 2:6:2 body layout with no layout mutation; tall header ASCII is handled inside the logo box rather than by resizing the page structure.
- Added regression tests for canonical tokens, panel labels, ASCII dimensions, header rendering guarantees, and placeholder-logo prevention.
- Kept canonical token tests active and marked visual screenshot review as `MANUAL_REVIEW_REQUIRED` for this pass.

## 7.10.7 - Logo Rendering Audit and Repair

- Added theme graphic asset registry validation for active WAR ROOM logo assets.
- Added logo normalization utilities for BOM stripping, line-ending normalization, width/height measurement, and optional line padding.
- Repaired ARASAKA and EXCOMM/MILITARY header rendering around canonical full-size assets.
- Hardened header logo rendering with a fixed monospace font stack, no wrapping, preserved whitespace, and selectable text.
- Added theme and logo screenshot gallery export tooling for visual audit artifacts.
- Added visual regression coverage for logo registry validation, logo normalization, theme logo rendering, scrambled ASCII detection, and gallery paths.

## 7.10.6 - Integrity and Self-Audit Layer

- Added active tree manifest tooling with SHA256 hashes, file sizes, and modification timestamps while excluding archive, legacy, runtime, generated, cache, and log roots.
- Added active manifest verification with CLEAN, DRIFT, and UNKNOWN reporting plus approval mode for writing a new baseline.
- Integrated active manifest and integrity verification output into runtime bundles.
- Added GUI diagnostics integrity status and a command palette action for integrity verification.
- Added regression coverage for active manifests, integrity drift detection, runtime bundle integrity artifacts, and GUI integrity status.

## 7.10.5 - Operator Workflow Layer

- Added a Ctrl+K command palette overlay for runtime snapshots, provider status, latest verdict, diagnostics, runtime bundle export, verification, theme toggling, and decision trace viewing.
- Added runtime bundle export tooling with snapshot, provider report, latest trace, verification manifest, GUI screenshots, runtime log tails, and changelog excerpt.
- Added a decision trace viewer overlay with recent trace listing and proposal_id filtering.
- Added a header health badge sourced from the runtime snapshot health contract.
- Added operator workflow regression coverage for the command palette, runtime bundle export, decision trace viewer, and health badge.

## 7.10.4 - GUI Visual Runtime Verification

- Added hidden Flet GUI smoke tooling for startup validation.
- Added GUI screenshot capture tooling for initial WAR ROOM and diagnostics drawer states, with explicit MOCK mode for unit-only checks.
- Added visual invariant checks for the 2:6:2 layout, diagnostics overlay behavior, provider status block, active model list, and duplicate panel guards.
- Added GUI launch, screenshot export, and visual invariant regression tests.

## 7.10.3 - Operational Observability Layer

- Added runtime snapshot tooling with provider status, model state, render/layout guards, latest decision trace, latest runtime log, and verification manifest path.
- Added a decision trace reader that tolerates missing files and corrupt JSONL lines.
- Added a GUI diagnostics drawer exposed as an overlay so the main WAR ROOM layout proportions remain unchanged.
- Added observability regression tests for runtime snapshots, decision trace reads, and the diagnostics drawer.

## 7.10.2 - Local Verification Tooling

- Added `tools/run_tests.py` for pytest-free script test discovery, execution, PASS/FAIL summaries, and verification manifest export.
- Added optional pytest dev extra without adding pytest to runtime dependencies.
- Added `reports/verification_v7.10.2.json` manifest output with version, timestamp, Python executable, tests run, pass/fail, and durations.
- Added `tools/provider_status_report.py` for local provider/backend/endpoint/model/degraded-state reporting.

## 7.10.1 - Provider and Voting Hardening

- Consolidated provider resolution around a single Msty-first resolver, added endpoint validation metadata, and exposed model availability reports.
- Enforced closed proposal taxonomy, confidence thresholds, quorum filtering, and deterministic NO_CONSENSUS/ESCALATE classifier failure behavior.
- Added JSONL decision trace logging with proposal_id, taxonomy, votes, and final verdict.
- Extended the WAR ROOM status panel with provider models and Codex/dev runtime status while keeping the existing layout proportions.
- Added provider resolver, classifier failure, GUI repaint regression, and active compile coverage.

## 7.10.0 - Deterministic Arbiter Consensus

- Added spec-shaped voting fields for evidence quality, critical risk, Arbiter-assigned domain relevance, and validation errors.
- Reworked consensus resolution around deterministic majority, CAUTION, NO_CONSENSUS, and priority tie-break branches.
- Updated monolith prompts, vote parsing, mock runtime output, UI status colors, TTS mappings, runtime config, and focused consensus tests.
- Routed Bellator feed packet versions through the canonical system version.

## 7.9.5 - ACLED OAuth Auth Fix

- Migrated ACLED feed authentication to OAuth/access-token resolution with legacy API key compatibility gated behind explicit opt-in.

## 7.9.4 - Bellator Geospatial Relevance

- Added Bellator geospatial filtering, strategic region presets, and strategic relevance scoring for feed intelligence.

## 7.9.3 - Active Tree Compile Hygiene

- Added active-tree compile hygiene script excluding archive/runtime directories.

## 7.9.2 - Bellator Feed Health Diagnostics

- Added Bellator feed API key health validation and PowerShell setup diagnostics.

## 7.9.1 - Bellator Intelligence Diagnostics

- Added Bellator Intelligence diagnostics UI summary and anti-fabrication feed handling guard.

## 7.9.0 - Bellator Feed Intelligence Layer

- Added Bellator Feed Intelligence Layer with ACLED, NASA FIRMS, Cloudflare Radar, and URLHaus Phase 1 clients.

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
