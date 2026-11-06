#Requires -Version 5.1
<#
.SYNOPSIS
Lists what keeps the portable SSD busy, so `chkdsk <drive> /f` can lock it.

.DESCRIPTION
Read-only. Shows running programs started from the drive or with it as their working folder in the
command line, and scheduled tasks whose action runs from it. Stop those, then run chkdsk from an
administrator prompt. Programs that only have a file open on the drive are not visible here.
#>
[CmdletBinding()]
param(
    [string]$Drive
)

# $PSCommandPath is empty in parameter defaults on Windows PowerShell 5.1, so default here.
if (-not $Drive) { $Drive = Split-Path -Qualifier $PSCommandPath }
$Drive = $Drive.TrimEnd("\").ToUpperInvariant()
$prefix = "$Drive\"
$quoted = "`"$Drive\"

Write-Output "== Running programs using $Drive =="
Get-CimInstance Win32_Process |
    Where-Object {
        ($_.ExecutablePath -and $_.ExecutablePath.ToUpperInvariant().StartsWith($prefix)) -or
        ($_.CommandLine -and ($_.CommandLine.ToUpperInvariant().Contains(" $prefix") -or $_.CommandLine.ToUpperInvariant().Contains($quoted)))
    } |
    Sort-Object Name |
    ForEach-Object { "{0} (pid {1})" -f $_.Name, $_.ProcessId }

Write-Output ""
Write-Output "== Scheduled tasks that run from $Drive =="
Get-ScheduledTask |
    Where-Object {
        $_.Actions | Where-Object {
            ("$($_.Execute) $($_.Arguments) $($_.WorkingDirectory)").ToUpperInvariant().Contains($prefix)
        }
    } |
    ForEach-Object { "{0}{1} [{2}]" -f $_.TaskPath, $_.TaskName, $_.State }
