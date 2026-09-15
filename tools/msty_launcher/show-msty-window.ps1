#Requires -Version 5.1
[CmdletBinding()]
param([switch]$InspectOnly)

$ErrorActionPreference = "Stop"

if (-not ("MstyWindowNative" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class MstyWindowNative
{
    public delegate bool EnumWindowsCallback(IntPtr window, IntPtr parameter);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsCallback callback, IntPtr parameter);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr window, StringBuilder text, int count);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr window);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr window, int command);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr window);
}
"@
}

$mstyProcessIds = @(
    Get-Process -Name "MstyStudio" -ErrorAction SilentlyContinue |
        Where-Object {
            try {
                $_.Path -like "*\MstyStudio.exe"
            } catch {
                $false
            }
        } |
        Select-Object -ExpandProperty Id
)

if ($mstyProcessIds.Count -eq 0) {
    throw "Msty Studio is not running."
}

$windows = [System.Collections.Generic.List[object]]::new()
$callback = [MstyWindowNative+EnumWindowsCallback]{
    param([IntPtr]$window, [IntPtr]$parameter)

    [uint32]$processId = 0
    [void][MstyWindowNative]::GetWindowThreadProcessId($window, [ref]$processId)
    if ($mstyProcessIds -contains [int]$processId) {
        $text = [System.Text.StringBuilder]::new(1024)
        [void][MstyWindowNative]::GetWindowText($window, $text, $text.Capacity)
        $windows.Add([pscustomobject]@{
            Handle = $window
            ProcessId = [int]$processId
            Title = $text.ToString()
            Visible = [MstyWindowNative]::IsWindowVisible($window)
        })
    }
    return $true
}

[void][MstyWindowNative]::EnumWindows($callback, [IntPtr]::Zero)

$candidate = $windows |
    Where-Object { $_.Title -match "(?i)msty" } |
    Select-Object -First 1

if (-not $InspectOnly -and $null -ne $candidate) {
    # SW_RESTORE restores a minimized or hidden top-level window.
    [void][MstyWindowNative]::ShowWindow($candidate.Handle, 9)
    [void][MstyWindowNative]::SetForegroundWindow($candidate.Handle)
}

$windows | Select-Object Handle,ProcessId,Title,Visible

if (-not $InspectOnly -and $null -eq $candidate) {
    throw "No Msty Studio top-level window was found."
}
