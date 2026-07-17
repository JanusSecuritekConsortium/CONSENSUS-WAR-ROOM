param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BootArgs
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Error "CONSENSUS virtual environment is missing. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e ."
    exit 1
}

$Arguments = @((Join-Path $Root "tools\boot.py"))
if ($BootArgs) {
    $Arguments += $BootArgs
}

& $Python @Arguments
exit $LASTEXITCODE
