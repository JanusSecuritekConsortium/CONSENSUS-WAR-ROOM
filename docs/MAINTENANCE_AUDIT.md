# CONSENSUS Maintenance Audit

Audit date: 2026-05-09

Version inspected: 7.5.0

Scope: `G:\CONSENSUS_SYSTEM`, with adjacent-path existence checks only for paths referenced by current or legacy files.

No files were moved or deleted during this audit. This is intentionally report-only, so the system version remains unchanged.

## Executive Summary

- Root hygiene is good. The project root contains only active entrypoints, documentation, active folders, `archive/`, `_ARBITER/`, and `.git`.
- Active modular source is small and clean compared with runtime and legacy payloads.
- The largest disk pressure is not active source. It is `_ARBITER/tts_audio` at roughly 139 GB and `archive/pre_modular_backups` at roughly 31.8 GB.
- The active provider config is aligned with current requirements: Msty Local AI at `http://localhost:11964`, Ollama fallback at `http://127.0.0.1:11434`, and the expected four monolith model assignments.
- Active scripts are path-relative. Legacy launchers under `_ARBITER` still contain stale absolute paths.
- Generated Python caches are present in active folders, `_ARBITER`, and archive trees. They are safe cleanup candidates, but were not deleted in this pass.
- Exact duplicate config backups exist in `_ARBITER/backups`. They are safe archive/consolidation candidates after a backup-retention rule is chosen.

## Active Source Folders

These are the active modular folders compiled by `python main.py --compile-active`:

- `core/`
- `config/`
- `integrations/`
- `ui/`
- `monoliths/`
- `tests/`
- `scripts/`
- `static/`

Active root entrypoints:

- `main.py`
- `consensus_war_room_genesis.py`

Active documentation:

- `CHANGELOG.md`
- `CONSENSUS_ARCHITECTURE.md`
- `MSTY_STUDIO_INTEGRATION.md`
- `docs/MAINTENANCE_AUDIT.md`

## Root Hygiene

Allowed root files found:

- `main.py`
- `consensus_war_room_genesis.py`
- `CHANGELOG.md`
- `CONSENSUS_ARCHITECTURE.md`
- `MSTY_STUDIO_INTEGRATION.md`

Allowed root folders found:

- `core`
- `config`
- `integrations`
- `ui`
- `monoliths`
- `static`
- `tests`
- `scripts`
- `archive`
- `_ARBITER`

Other root folders:

- `.git`

Unexpected old root `.py` files: none.

No files were moved to `archive/legacy_root/`.

## Size and Clutter Inventory

Approximate top-level folder sizes:

| Path | Approx. size | Files | Assessment |
| --- | ---: | ---: | --- |
| `_ARBITER/` | 139135.62 MB | 36503 | Runtime data plus large legacy TTS assets. |
| `archive/` | 31931.63 MB | 46127 | Legacy/pre-modular backups and archived experiments. |
| `ui/` | 0.19 MB | 39 | Active source. |
| `core/` | 0.16 MB | 62 | Active source. |
| `tests/` | 0.12 MB | 55 | Active tests. |
| `integrations/` | 0.07 MB | 14 | Active provider integrations. |
| `config/` | 0.02 MB | 12 | Active config code. |
| `static/` | 0.01 MB | 9 | Active logo assets. |
| `scripts/` | ~0 MB | 1 | Active launcher. |
| `monoliths/` | ~0 MB | 14 | Active profiles and registry. |

Largest `_ARBITER` subtrees:

| Path | Approx. size | Files | Assessment |
| --- | ---: | ---: | --- |
| `_ARBITER/tts_audio/` | 139076.25 MB | 36026 | Very large voice/TTS asset and environment payload. Not part of active compile. |
| `_ARBITER/Bot/` | 55.52 MB | 114 | Legacy bot/runtime files. Excluded from active compile. |
| `_ARBITER/logs/` | 2.39 MB | 14 | Runtime logs; rotation policy recommended. |
| `_ARBITER/backups/` | 0.98 MB | 290 | Many duplicate historical configs. |
| `_ARBITER/theme_previews/` | 0.04 MB | 8 | Generated preview exports. |
| `_ARBITER/memory/` | 0.03 MB | 3 | Active persistent memory. Keep. |
| `_ARBITER/exports/` | 0.02 MB | 1 | Generated session export. |
| `_ARBITER/tmp_votes/` | ~0 MB | 3 | Runtime vote scratch files. |

Largest `archive` subtrees:

| Path | Approx. size | Files | Assessment |
| --- | ---: | ---: | --- |
| `archive/pre_modular_backups/` | 31809.84 MB | 45430 | Large historical backups, including dependency/cache payloads. |
| `archive/old_experiments/` | 119.67 MB | 685 | Historical experiments. |
| `archive/legacy_monoliths/` | 2.06 MB | 6 | Legacy monolith files. |
| `archive/imported_demos/` | 0.05 MB | 2 | Imported demos. |
| `archive/old_launchers/` | ~0 MB | 3 | Old launchers. |

## Generated Folders and Cache Artifacts

Generated cache folders found:

- Active source caches: `core/**/__pycache__`, `config/__pycache__`, `integrations/**/__pycache__`, `ui/**/__pycache__`, `monoliths/**/__pycache__`, `tests/__pycache__`
- Runtime/legacy caches: `_ARBITER/__pycache__`, `_ARBITER/Bot/**/__pycache__`, `_ARBITER/tts_audio/**/__pycache__`
- Archive caches: `archive/**/__pycache__`

Generated or disposable file categories found:

- `.pyc` files under active source, `_ARBITER`, and archive trees.
- `python -m compileall ...` may create a top-level `__pycache__/` for `main.py` and `consensus_war_room_genesis.py`; this is generated cache and safe to remove.
- Empty runtime logs: `_ARBITER/genesis_api.log`, `_ARBITER/genesis_api.err.log`, `_ARBITER/logs/phase3b_api_stdout.log`, `_ARBITER/logs/phase3b_api_stderr.log`.
- Generated preview exports under `_ARBITER/theme_previews/`.
- Runtime session export under `_ARBITER/exports/`.

Recommended cleanup:

- Delete active `__pycache__` folders and `.pyc` files when the workspace is quiet.
- Keep `_ARBITER/memory`, `_ARBITER/decision_history.json`, and `_ARBITER/logs/system.jsonl`.
- Add a retention policy before deleting historical `_ARBITER/logs/*.log`, `_ARBITER/backups/*.json`, or generated previews.

## Duplicate Detection

Filename duplicates found:

- `__init__.py`: expected across Python packages.
- `registry.py`: expected in `core/knowledge` and `monoliths`.
- `retrieval.py`: expected in `core/memory` and `core/knowledge`.
- `.gitkeep`: expected in `static` and `ui/assets`.
- `runtime.py`: expected in `config` and `integrations/msty`.
- `engine.py`: active `core/voting/engine.py` and legacy `_ARBITER/Bot/Voice/glados-tts-main/engine.py`.
- `anima_bot.py`: `_ARBITER/Bot/anima_bot.py` and `_ARBITER/Bot/OLD/anima_bot.py`.
- `glados.py`: `_ARBITER/glados.py` and `_ARBITER/Bot/Voice/glados-tts-main/glados.py`.
- `LICENSE`: duplicated within embedded legacy voice dependencies.

Exact duplicate hashes found:

- `_ARBITER/glados.py` and `_ARBITER/Bot/Voice/glados-tts-main/glados.py` are identical.
- Many `_ARBITER/backups/config_*.json` files are exact duplicates of each other and of older `_ARBITER/config.json` states.
- Empty log files and empty legacy package `__init__.py` files share the empty-file hash.
- `static/.gitkeep` and `ui/assets/.gitkeep` are identical by design.

No duplicate files were moved. Recommended next action is a dedicated backup retention phase:

- Keep `_ARBITER/genesis_config.json` as active runtime config.
- Keep a small number of dated backup configs.
- Move duplicate backup configs to `archive/duplicates/config_backups/` or delete them after explicit approval.

## Hardcoded Path Findings

Active/config-driven path references:

- `core/paths.py` centralizes `_ARBITER` paths using `SYSTEM_ROOT / "_ARBITER"`.
- `core/cli.py` writes previews and exports under `_ARBITER`.
- Documentation references `G:\CONSENSUS_SYSTEM` as an operator path.
- Runtime logs contain historical absolute paths. These are records, not live configuration.

Stale or risky absolute paths:

- `_ARBITER/launch_war_room.bat` contains `cd /d J:\CONSENSUS_SYSTEM\_ARBITER`. `J:\CONSENSUS_SYSTEM` was not present during this audit.
- `_ARBITER/Bot/anima_launcher.bat` contains `cd "F:\ANIMA - AI Agent\Bot"` and a user-specific Python path under `C:\Users\JMaje\...`. `F:\` exists, but this is outside the active CONSENSUS runtime and was not touched.

Generated files with absolute project paths:

- `_ARBITER/theme_previews/*.txt` include logo source paths such as `G:\CONSENSUS_SYSTEM\static\logos\...`.
- `_ARBITER/decision_history_genesis.json` and `_ARBITER/logs/system.jsonl` include historical `G:\CONSENSUS_SYSTEM\...` paths.

No active Python imports were found that require `G:\`, `J:\`, `F:\`, `I:\`, or `C:\Users\...` hardcoding.

Adjacent path existence checks:

| Path | Exists | Action |
| --- | --- | --- |
| `G:\AI_MODELS` | yes | Not scanned; no active config reference requiring it. |
| `G:\webseer` | yes | Not scanned; no active config reference requiring it. |
| `J:\CONSENSUS_SYSTEM` | no | Referenced by stale legacy launcher only. |
| `J:\AI_MODELS` | no | Not referenced by active config. |
| `J:\webseer` | no | Not referenced by active config. |
| `F:\` | yes | Referenced by legacy Anima launcher; outside active runtime. |

## Launcher Audit

Active launcher:

- `scripts/start_genesis_api_msty.bat`
  - Uses `cd /d "%~dp0.."`.
  - Launches `python consensus_war_room_genesis.py --api --backend msty-local --theme eva`.
  - No stale absolute path found.

Legacy launchers:

- `_ARBITER/launch_war_room.bat`
  - Uses missing `J:\CONSENSUS_SYSTEM\_ARBITER`.
  - Launches legacy `_ARBITER/arbiter_gui.py`, not the modular GUI entrypoint.
  - Recommended: archive or replace with `python main.py --gui --theme eva` in a later script-cleanup phase.

- `_ARBITER/launch_arbiter_autoboot.bat`
  - Contains simulated placeholder content.
  - Recommended: archive if not used.

- `_ARBITER/Bot/anima_launcher.bat`
  - Uses `F:\ANIMA - AI Agent\Bot` and a user-specific Python 3.13 path.
  - This is outside the active CONSENSUS runtime. Leave until the Anima path is explicitly reviewed.

- Embedded TTS launchers under `_ARBITER/tts_audio/**`
  - Belong to bundled voice/RVC tooling, not active CONSENSUS launch flow.
  - Do not edit without a separate TTS maintenance task.

## Config Audit

Active config file:

- `_ARBITER/genesis_config.json`

Current provider configuration:

- `msty_base_url`: `http://localhost:11964`
- `ollama_base_url`: `http://127.0.0.1:11434`
- `msty_llama_cpp_base_url`: empty
- `mock_fallback_enabled`: `true`
- `strict_provider_mode`: `false`
- `use_available_model_fallback`: `false`

Required model mapping:

| Monolith | Configured model | Status |
| --- | --- | --- |
| `ARBITER` | `qwen3:latest` | Expected current mapping. |
| `RATIONALIS` | `deepseek-coder-33b-instruct.Q4_K_S:latest` | Expected current mapping. |
| `AETERNUM` | `yi-34b-chat.Q4_K_S:latest` | Expected current mapping. |
| `BELLATOR` | `cogito:latest` | Expected current mapping. |

Obsolete `mistral:latest` mapping:

- Not present in active `_ARBITER/genesis_config.json`.
- May still appear in historical logs or tests that intentionally simulate fallback behavior.

## Archive Manifest

No files were moved into `archive/` during this audit, so `archive/ARCHIVE_MANIFEST.md` was not changed.

## Broken References Fixed

None. This pass did not edit code, config, scripts, or launchers.

Broken or stale references left as explicit cleanup candidates:

- `_ARBITER/launch_war_room.bat` points at missing `J:\CONSENSUS_SYSTEM\_ARBITER`.
- `_ARBITER/launch_arbiter_autoboot.bat` is placeholder/simulated.

## Recommended Follow-Up Cleanup Plan

1. Cache cleanup:
   - Delete active `__pycache__` folders and `.pyc` files.
   - Delete root `__pycache__/` if it appears after compile verification.
   - Optionally delete archive and legacy `__pycache__` folders.

2. Legacy launcher cleanup:
   - Move `_ARBITER/launch_war_room.bat` and `_ARBITER/launch_arbiter_autoboot.bat` to `archive/old_launchers/` or replace with modular launchers.
   - Update `archive/ARCHIVE_MANIFEST.md` if moved.

3. Backup retention:
   - Keep `_ARBITER/genesis_config.json`.
   - Keep the latest N backup configs.
   - Move exact duplicate config backups to `archive/duplicates/config_backups/` or delete after explicit approval.

4. Runtime log retention:
   - Keep `_ARBITER/logs/system.jsonl` unless exported/rotated.
   - Move old dated logs into `archive/logs/` or compress them.

5. TTS payload review:
   - `_ARBITER/tts_audio/` is the dominant disk consumer at roughly 139 GB.
   - Do not delete automatically. First confirm which voice models and raw audio are still needed.

6. Archive compaction:
   - `archive/pre_modular_backups/` contains large dependency/runtime payloads.
   - Consider compressing or moving it to cold storage after confirming no active references.

## Remaining Risks

- `_ARBITER/tts_audio` and `archive/pre_modular_backups` together dominate disk usage. They are outside active compile boundaries but still inside the project tree.
- Legacy `_ARBITER` scripts can confuse operators because they coexist with modular CLI entrypoints.
- Runtime logs and preview exports intentionally contain absolute paths; these are harmless for execution but noisy for path audits.
- Exact duplicate config backups are numerous, but no retention policy exists yet.
- Adjacent paths `G:\AI_MODELS`, `G:\webseer`, and `F:\` were not deeply scanned because no active config required it and the safety rule says not to touch user data outside the project.
