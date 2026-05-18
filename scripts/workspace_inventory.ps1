param(
    [string]$WorkspaceRoot = "G:\",
    [int]$MaxItems = 200
)

$ErrorActionPreference = "SilentlyContinue"

function Show-Section {
    param([string]$Title)
    Write-Output ""
    Write-Output "== $Title =="
}

Show-Section "Top-level workspace"
Get-ChildItem -Force -Path $WorkspaceRoot |
    Select-Object Name, FullName, Mode, Length, LastWriteTime |
    Format-Table -AutoSize

Show-Section "Msty Studio"
Get-ChildItem -Force -Path (Join-Path $WorkspaceRoot "Msty\MstyStudio") |
    Select-Object Name, FullName, Mode, Length, LastWriteTime |
    Format-Table -AutoSize

Show-Section "AI model folders"
Get-ChildItem -Force -Directory -Path (Join-Path $WorkspaceRoot "AI_MODELS") -Recurse |
    Where-Object { $_.FullName.Split('\').Count -le 4 } |
    Select-Object -First $MaxItems FullName, LastWriteTime |
    Format-Table -AutoSize

Show-Section "TARS"
Get-ChildItem -Force -Path (Join-Path $WorkspaceRoot ".TARS") |
    Select-Object Name, FullName, Mode, Length, LastWriteTime |
    Format-Table -AutoSize

Show-Section "Consensus Obsidian vault"
Get-ChildItem -Force -File -Path (Join-Path $WorkspaceRoot "Obsidian\CONSENSUS_SYSTEM") -Recurse |
    Select-Object -First $MaxItems FullName, Length, LastWriteTime |
    Format-Table -AutoSize

Show-Section "Kiwix/Msty Consensus corpus"
Get-ChildItem -Force -Directory -Path (Join-Path $WorkspaceRoot "Kiwix\Kowledge Stack Msty") -Recurse |
    Where-Object { $_.FullName -match "CONSENSUS|TARS|Msty|PsiCorpus" } |
    Select-Object -First $MaxItems FullName, LastWriteTime |
    Format-Table -AutoSize
