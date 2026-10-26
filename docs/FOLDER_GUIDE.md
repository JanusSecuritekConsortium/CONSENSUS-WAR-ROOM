# Folder guide

Updated 2026-10-09.

| Location | Purpose |
| --- | --- |
| `dist/CONSENSUS.exe` | Current Windows desktop executable; stable taskbar target |
| `core/`, `ui/`, `config/`, `integrations/`, `assistant/`, `voice/`, `monoliths/` | Active application modules |
| `static/` | Logos, icons and other application assets |
| `docs/` | Documentation |
| `tests/` | Existing automated checks |
| `tools/` | Development and operator utilities |
| `tools/launchers/` | API launcher and workspace inventory helper, formerly in `scripts/` |
| `tools/packaging/` | Windows version metadata, formerly in `packaging/` |
| `_ARBITER/`, `logs/` | Active runtime state and logs |
| `reports/` | Current reports and history used by the app |
| `reports/history/` | Superseded verification, manifest, visual-review and export files |
| `.local/build/`, `.local/cache/pytest/` | Generated build work and test cache |
| `archive/` | Historical source; inactive prototypes are grouped in `archive/prototypes/` |
| `external/` | Existing third-party sources required by voice integrations |

The newest report in each archived family remains at its original report-root path for existing export fallbacks. Runtime histories, verdicts, dossiers, screenshots and `dist/_ARBITER` / `dist/reports` keep their paths.

Older executable copies and feature build snapshots are grouped outside the source tree under `G:\Backup\Consensus`. Historical personal notes formerly in root `memory/` are preserved with provenance in the canonical private vault; active session memory remains under `_ARBITER/memory/`.

Primary launchers, requirements, project configuration and top-level documentation stay at the repository root. `build_exe.py` uses `.local/build/` for its working files, and pytest uses `.local/cache/pytest/`.
