# Msty CONSENSUS Launcher

Canonical launcher version: `MstyConsensusLauncher v1.1.3`

Operational status: `ACCEPTED / RELEASE-STABLE`

## Canonical Files

Primary launcher:

```text
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe
```

Backup launcher:

```text
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher-1.1.3.exe
```

Config:

```text
G:\Tools\MstyConsensusLauncher\launcher.config.json
```

Logs:

```text
G:\Msty\logs
```

Regression:

```text
G:\Tools\MstyConsensusLauncher\regression-test.ps1
```

Launcher-local README:

```text
G:\Tools\MstyConsensusLauncher\README.md
```

## Purpose

`MstyConsensusLauncher` is the CONSENSUS boot wrapper for Windows. It keeps startup behavior deterministic enough for daily use while avoiding duplicate Msty or CONSENSUS processes.

The launcher:

- Starts Msty services only when needed.
- Waits for semantic Msty API readiness.
- Selects the first usable primary or fallback Msty API endpoint.
- Launches `G:\CONSENSUS_SYSTEM\dist\CONSENSUS.exe` only when Msty is ready.
- Injects the selected Msty endpoint into the launched CONSENSUS child process environment.
- Exits without terminating Msty services.

## Required Operator Commands

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --status
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --status --json
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --self-test
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --diagnose-api
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --diagnose-port
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --print-config --json
powershell -ExecutionPolicy Bypass -File G:\Tools\MstyConsensusLauncher\regression-test.ps1
```

## Startup Integration

The Windows Startup shortcut must use:

```text
Target: G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe
Arguments: --startup
Working directory: G:\Tools\MstyConsensusLauncher
```

Repair shortcuts with:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --install-shortcuts
```

`--startup` applies the configured randomized boot delay before checking Msty readiness and launching CONSENSUS.

## Readiness Contract

CONSENSUS must not be launched merely because a port responds. Launcher v1.1.3 requires semantic readiness:

- `<api_url>/v1/models` returns HTTP `200`
- JSON parses successfully
- `data` array exists
- model count is at least `1`

The selected endpoint is visible in:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --status --json
```

Fields of interest:

```text
selected_msty_api_url
consensus_launch_endpoint
msty_model_count
msty_model_ids
fallback_probe_results
environment_injection_enabled
```

## Fallback Behavior

Current canonical config uses this primary endpoint:

```text
http://127.0.0.1:11454
```

Current canonical config uses this fallback endpoint:

```text
http://127.0.0.1:11964
```

Selection order:

1. Primary `msty_api_url`
2. Fallback URLs, in configured order, when `allow_fallback_api` is `true`
3. First semantically-ready endpoint wins

Logs:

```text
API_PRIMARY_NOT_READY <url>
API_FALLBACK_PROBE <url>
API_FALLBACK_READY <url> count=<n>
API_SELECTED <url>
API_NO_ENDPOINT_READY
```

## Environment Injection

When launching CONSENSUS, v1.1.3 injects the selected endpoint into the child process environment:

```json
{
  "CONSENSUS_MSTY_BASE_URL": "{selected_msty_api_url}",
  "AURELIUS_MSTY_BASE_URL": "{selected_msty_api_url}",
  "MSTY_BASE_URL": "{selected_msty_api_url}"
}
```

This affects only the launched CONSENSUS process. It does not write global Windows environment variables, registry keys, or CONSENSUS config files.

Disable with:

```json
{
  "enable_consensus_environment_injection": false
}
```

## Recovery Behavior

If known Msty/MstyClaw processes are running but semantic readiness never arrives, stale recovery can terminate only known Msty/MstyClaw process names from config, wait briefly, relaunch Msty, and wait for readiness again.

Use `--no-recover` to disable process termination.

## Window Visibility

Launcher v1.1.3 adds `msty_window_mode` in:

```text
G:\Tools\MstyConsensusLauncher\launcher.config.json
```

Supported values:

```text
normal
minimized
hidden
```

Default:

```text
minimized
```

Behavior:

- `normal`: launch Msty normally.
- `minimized`: launch Msty minimized. This is the canonical default.
- `hidden`: best-effort hide for known Msty windows after startup while keeping all Msty processes running.

`hidden` is best-effort because some Msty services have no main window handle or create windows late. `MSTY_WINDOW_HANDLE_NOT_FOUND` is non-fatal; the launcher logs it and continues without killing Msty or touching unrelated processes.

Closing or exiting `MstyConsensusLauncher.exe` must not terminate Msty services. Msty readiness is still verified through `/v1/models`.

## Shortcut Self-Test Notes

The Startup shortcut remains a critical self-test requirement because it controls Windows boot integration:

```text
Target: G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe
Arguments: --startup
Working directory: G:\Tools\MstyConsensusLauncher
```

The Start Menu shortcut is for pinning/operator convenience. In some non-elevated contexts, Windows COM shortcut metadata can be unreadable or blank even when the shortcut exists. Launcher v1.1.3 may report Start Menu shortcut metadata as warning-only without elevation.

## Troubleshooting

| Problem | Command | Expected Signal |
| --- | --- | --- |
| Startup is broken | `--self-test` | Startup shortcut should be `VALID`. |
| API is down | `--diagnose-api` | Shows HTTP status, JSON validity, model count, and selected endpoint. |
| Port is occupied | `--diagnose-port` | Shows listener PID, process name, and executable path when available. |
| Wrong endpoint is used | `--status --json` | Inspect `selected_msty_api_url` and `fallback_probe_results`. |
| CONSENSUS cannot see Msty | `--status --json` | Confirm `consensus_launch_endpoint` and environment injection fields. |
| Config is confusing | `--print-config --json` | Shows effective config after defaults, with sensitive values redacted. |
| Launcher exits immediately | `--tail-log` | Look for `INSTANCE_ALREADY_RUNNING`. |
| Regression concern | `regression-test.ps1` | Should complete with `Regression checks passed.` |

## Freeze Decision

`MstyConsensusLauncher v1.1.3` is the canonical release-stable launcher. Feature work should stop here unless a real startup, recovery, or CONSENSUS integration bug appears.
