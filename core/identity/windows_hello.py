"""Windows Hello (fingerprint, face or the Windows PIN) as a shortcut for a profile.

Windows does the check and only reports the outcome; CONSENSUS never sees a
fingerprint or the Windows PIN. Hello proves "the signed-in Windows user is
present", so it is only offered for a profile that has it switched on.
"""
from __future__ import annotations

import subprocess
import sys

_PRELUDE = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Security.Credentials.UI.UserConsentVerifier,Windows.Security.Credentials.UI,ContentType=WindowsRuntime] | Out-Null
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($operation, $resultType) {
    $task = $asTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait() | Out-Null
    $task.Result
}
"""
_AVAILABLE = _PRELUDE + r"""
Await ([Windows.Security.Credentials.UI.UserConsentVerifier]::CheckAvailabilityAsync()) `
    ([Windows.Security.Credentials.UI.UserConsentVerifierAvailability])
"""
_VERIFY = _PRELUDE + r"""
Await ([Windows.Security.Credentials.UI.UserConsentVerifier]::RequestVerificationAsync($env:CONSENSUS_HELLO_MESSAGE)) `
    ([Windows.Security.Credentials.UI.UserConsentVerificationResult])
"""


def _run(script: str, timeout: float, message: str = "") -> str:
    if sys.platform != "win32":
        return ""
    import os

    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "CONSENSUS_HELLO_MESSAGE": message},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip().splitlines()[-1].strip() if completed.returncode == 0 and completed.stdout.strip() else ""


def hello_available(run=_run) -> bool:
    """True when this PC has Windows Hello set up for the signed-in Windows user."""
    return run(_AVAILABLE, 20) == "Available"


def request_hello(message: str = "Unlock CONSENSUS", run=_run) -> bool:
    """Show the Windows Hello prompt. True only when Windows reports the user verified."""
    return run(_VERIFY, 120, message) == "Verified"
