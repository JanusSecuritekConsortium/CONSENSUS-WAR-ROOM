# MstyConsensusLauncher v1.1.3

`MstyConsensusLauncher` is the canonical Windows boot wrapper for keeping Msty available and launching CONSENSUS against the same semantically-ready Msty backend.

Release state: `ACCEPTED / RELEASE-STABLE`

Canonical release-stable launcher: `MstyConsensusLauncher v1.1.3`

## Purpose

The launcher coordinates three boot-time concerns:

- Avoid duplicate Msty and CONSENSUS processes.
- Wait for a usable Msty `/v1/models` endpoint before launching CONSENSUS.
- Inject the selected Msty API base URL into the launched CONSENSUS child process environment.

The launcher is intentionally ephemeral. It starts or repairs what is needed, launches CONSENSUS when appropriate, then exits. It is not a resident tray process.

## Paths

Primary EXE:

```text
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe
```

Backup EXE:

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

Regression test:

```text
G:\Tools\MstyConsensusLauncher\regression-test.ps1
```

## Supported Flags

```text
--startup
--no-recover
--self-test
--status
--status --json
--print-config
--print-config --json
--install-shortcuts
--diagnose-port
--diagnose-api
--open-logs
--tail-log
--help
```

## Normal Usage

Daily operator status:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --status
```

Machine-readable status:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --status --json
```

Full diagnostic self-test:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --self-test
```

Inspect effective config:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --print-config --json
```

Run the regression suite:

```powershell
powershell -ExecutionPolicy Bypass -File G:\Tools\MstyConsensusLauncher\regression-test.ps1
```

## Startup Behavior

The Windows Startup shortcut should point to:

```text
Target: G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe
Arguments: --startup
Working directory: G:\Tools\MstyConsensusLauncher
```

In `--startup` mode, the launcher waits a randomized delay from config before booting services. This reduces startup contention during Windows login.

Repair shortcuts with:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --install-shortcuts
```

### Background watchdog

The Startup launcher is intentionally ephemeral, so it does not restart Msty
after a later crash or manual exit. The per-user scheduled task
`Msty Background Watchdog` closes that gap by running:

```text
G:\Tools\MstyConsensusLauncher\msty-background-watchdog.ps1 -EnsureClaw
```

The watchdog starts 15 seconds after user sign-in, keeps Msty Studio minimized
but accessible from the taskbar, checks Msty Local AI on port `11964` (the
provider used by Msty Go) and the llama.cpp provider on port `11454` every 30
seconds, and invokes
`G:\Msty\keep-msty-running.ps1` after four consecutive API failures. It also
starts Msty Go once when the watchdog begins. Task Scheduler is configured to
restart the watchdog after an unexpected exit.

Operational checks:

```powershell
Get-ScheduledTask -TaskName "Msty Background Watchdog"
Get-Content G:\Msty\logs\msty-background-watchdog.log -Tail 20
powershell -ExecutionPolicy Bypass -File G:\Tools\MstyConsensusLauncher\msty-background-watchdog.ps1 -EnsureClaw -Once
```

## Config

The launcher loads:

```text
G:\Tools\MstyConsensusLauncher\launcher.config.json
```

If the file is missing, the launcher creates it with defaults. If the file is malformed, the launcher logs `CONFIG_INVALID` and exits with code `1`.

Important fields:

- `msty_api_url`: primary Msty API endpoint. Default: `http://127.0.0.1:11964`
- `fallback_msty_api_urls`: fallback endpoints. Default includes `http://127.0.0.1:11454`
- `allow_fallback_api`: enables fallback probing.
- `consensus_exe_path`: CONSENSUS executable path.
- `log_dir`: launcher log directory.
- `msty_window_mode`: Msty startup visibility mode. Supported values: `normal`, `minimized`, `hidden`. Default: `hidden`.
- `enable_stale_recovery`: enables stale Msty recovery.
- `consensus_environment_variables`: child-process environment templates.
- `enable_consensus_environment_injection`: enables child-process environment injection.

## Window Mode

`msty_window_mode` controls Msty startup visibility without making the launcher resident:

- `normal`: start Msty normally.
- `minimized`: start Msty minimized.
- `hidden`: start Msty without a visible window and best-effort hide known Msty windows already running. This is the default.

The launcher never terminates Msty merely to change visibility. If no known Msty window handle is available, it logs `MSTY_WINDOW_HANDLE_NOT_FOUND` and continues. That warning is non-fatal and does not mean Msty is down.

## Readiness

Msty readiness is semantic, not just port-based. An endpoint is ready only when:

- `<api_url>/v1/models` returns HTTP `200`
- response JSON parses
- a `data` array exists
- model count is at least `1`

CONSENSUS launches only after one endpoint meets those conditions.

## Recovery Behavior

If known Msty/MstyClaw processes exist but no semantic Msty API readiness is reached before timeout, stale recovery can terminate only known Msty/MstyClaw process names from config, wait briefly, relaunch Msty, and probe readiness again.

Disable termination with:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --no-recover
```

With `--no-recover`, stale state is logged but Msty processes are not killed.

## Fallback Endpoint Behavior

Readiness selection order:

1. Probe primary `msty_api_url`.
2. If primary is not ready and `allow_fallback_api` is `true`, probe each URL in `fallback_msty_api_urls`.
3. Select the first semantically-ready endpoint.

Relevant logs:

```text
API_PRIMARY_NOT_READY <url>
API_FALLBACK_PROBE <url>
API_FALLBACK_READY <url> count=<n>
API_SELECTED <url>
API_NO_ENDPOINT_READY
```

## Environment Injection

When CONSENSUS is launched, the selected Msty API URL is injected into the child process environment only. The launcher does not modify global Windows environment variables, registry values, or CONSENSUS config files.

Default variables:

```json
{
  "CONSENSUS_MSTY_BASE_URL": "{selected_msty_api_url}",
  "AURELIUS_MSTY_BASE_URL": "{selected_msty_api_url}",
  "MSTY_BASE_URL": "{selected_msty_api_url}"
}
```

Set `enable_consensus_environment_injection` to `false` to disable injection. When disabled, the launcher logs:

```text
CONSENSUS_ENV_INJECT_DISABLED
```

Sensitive environment variable names containing terms like `TOKEN`, `SECRET`, `PASSWORD`, `PASS`, `KEY`, or `CREDENTIAL` are redacted in logs and status/config output.

## Diagnostics

API diagnostics:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --diagnose-api
```

Port diagnostics:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --diagnose-port
```

Log access:

```powershell
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --open-logs
G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe --tail-log
```

## Troubleshooting

| Symptom | Check | Likely Fix |
| --- | --- | --- |
| CONSENSUS does not launch | Run `--self-test` and `--diagnose-api` | Ensure at least one `/v1/models` endpoint returns HTTP `200` with models. |
| Msty process exists but API is not ready | Run `--diagnose-port` and `--diagnose-api` | Use normal launcher recovery or rerun without `--no-recover`. |
| Startup launch does not happen | Run `--install-shortcuts`, then `--self-test` | Repair Startup shortcut target, arguments, and working directory. |
| Start Menu shortcut shows warning | Run elevated `--install-shortcuts` if pinning is needed | Start Menu shortcut metadata may be warning-only without elevation. Startup shortcut remains the critical self-test requirement. |
| Wrong backend selected | Run `--status --json` | Inspect `selected_msty_api_url`, fallback settings, and model probe results. |
| Environment variables not visible in CONSENSUS | Run `--status --json` | Confirm `environment_injection_enabled` is `true` and templates are configured. |
| Config failure | Run `--print-config --json` | Fix malformed JSON or invalid field types in `launcher.config.json`. |
| Logs are missing | Check `G:\Msty\logs` | Ensure `log_dir` exists or let the launcher recreate it. |
| Another launcher exits immediately | Check logs for `INSTANCE_ALREADY_RUNNING` | Wait for the active launcher instance to finish. |

## Release Policy

`v1.1.3` is the canonical release-stable boot wrapper. Do not add launcher features unless there is a concrete operational bug or integration requirement.
