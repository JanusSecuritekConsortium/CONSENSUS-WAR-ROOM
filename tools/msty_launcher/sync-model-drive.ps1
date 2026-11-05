#Requires -Version 5.1
<#
.SYNOPSIS
Points Msty Studio's llama.cpp model list at the drive letter the portable SSD has on this PC.

.DESCRIPTION
models-preset.ini stores each model as an absolute path (G:\AI_MODELS\...). When the SSD gets another
letter, every model fails to load. This rewrites a `model =` or `mmproj =` line only when its file is
missing and the same path exists on this script's drive. Nothing changes when the letters already match.
A copy of the previous file is kept as models-preset.ini.bak-drive. Msty Studio reads the list when its
llama.cpp server starts, so restart it after a change.
#>
[CmdletBinding()]
param(
    [string]$PresetPath,
    [string]$Drive,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not $Drive) { $Drive = Split-Path -Qualifier $PSCommandPath }
if (-not $PresetPath) { $PresetPath = Join-Path $Drive "Msty\MstyStudio\llama-cpp\models-preset.ini" }

if (-not (Test-Path -LiteralPath $PresetPath -PathType Leaf)) {
    Write-Output "MODEL_DRIVE_SKIPPED reason=no_preset path=$PresetPath"
    exit 0
}

# Keep Msty's own line endings: it writes LF without a final newline.
$text = [System.IO.File]::ReadAllText($PresetPath)
$newline = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
$lines = $text -split '\r?\n'
$changed = 0
$pattern = '^(?<key>\s*(model|mmproj)\s*=\s*)(?<letter>[A-Za-z]:)(?<rest>\\.*)$'

for ($i = 0; $i -lt $lines.Count; $i++) {
    $match = [regex]::Match($lines[$i], $pattern)
    if (-not $match.Success) { continue }
    $letter = $match.Groups["letter"].Value
    $rest = $match.Groups["rest"].Value
    if ($letter -ieq $Drive) { continue }
    if (Test-Path -LiteralPath ($letter + $rest)) { continue }
    $candidate = $Drive + $rest
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    $lines[$i] = $match.Groups["key"].Value + $candidate
    $changed++
}

if ($changed -eq 0) {
    Write-Output "MODEL_DRIVE_OK drive=$Drive"
    exit 0
}

if ($DryRun) {
    Write-Output "MODEL_DRIVE_WOULD_UPDATE drive=$Drive models=$changed"
    exit 0
}

Copy-Item -LiteralPath $PresetPath -Destination "$PresetPath.bak-drive" -Force
$encoding = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($PresetPath, ($lines -join $newline), $encoding)
Write-Output "MODEL_DRIVE_UPDATED drive=$Drive models=$changed restart_msty=true"
