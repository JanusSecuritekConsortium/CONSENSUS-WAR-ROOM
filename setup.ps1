# One-time setup for CONSENSUS on Windows. Run from the repository folder:
#     .\setup.bat            (or: powershell -ExecutionPolicy Bypass -File setup.ps1)
# It creates .venv, installs the program, runs a model-free test vote and the health check, then says
# whether Msty's model server is reachable and which voter models it already has. Safe to run again.
# Full guide: docs\REPRODUCE.md
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Step($text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }

Step "Looking for Python 3.10 or newer"
$candidates = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $candidates += ,@("py", "-3") }
if (Get-Command python -ErrorAction SilentlyContinue) { $candidates += ,@("python") }
$python = $null
foreach ($c in $candidates) {
    $exe = $c[0]; $extra = @($c | Select-Object -Skip 1)
    try {
        $ok = & $exe @extra -c "import sys; print(int(sys.version_info >= (3, 10)))" 2>$null
        if ($ok -eq "1") { $python = $c; break }
    } catch { }
}
if (-not $python) {
    Write-Host "Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "(tick 'Add python.exe to PATH'), then run this setup again."
    exit 1
}
$pyExe = $python[0]; $pyArgs = @($python | Select-Object -Skip 1)
& $pyExe @pyArgs --version

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Step "Creating the .venv folder"
    & $pyExe @pyArgs -m venv .venv
}

Step "Installing CONSENSUS and its Python packages (a few minutes the first time)"
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -r requirements.txt
& $venvPython -m pip install --quiet -e .
if ($LASTEXITCODE -ne 0) { Write-Host "Installing failed; see the messages above." -ForegroundColor Red; exit 1 }

Step "Test vote with simulated voters (no models needed)"
& $venvPython consensus_war_room_genesis.py --no-boot --backend mock "Should we proceed?" | Select-String "FINAL VERDICT"

Step "Health check (voice_files stays DEGRADED until you add optional voice models)"
& $venvPython consensus_war_room_genesis.py --health

Step "Checking Msty's model server at http://localhost:11454"
$check = @'
from config.runtime import load_runtime_config
from core.paths import CONFIG_PATH
from integrations.msty import api
config = load_runtime_config(CONFIG_PATH)
url = "http://localhost:11454"
try:
    import requests
    response = requests.get(url + "/v1/models", timeout=5)
    response.raise_for_status()
    available = [str(entry.get("id")) for entry in response.json().get("data", [])]
except Exception:
    print("NOT REACHABLE: install and open Msty Studio (docs/REPRODUCE.md, step 3).")
    raise SystemExit(0)
missing = 0
for agent in ("RATIONALIS", "AETERNUM", "BELLATOR", "ARBITER"):
    wanted = config.agent_model_overrides.get(agent) or config.base_model
    found = api.match_model_alias(wanted, available)[0]
    print(f"{agent:<11}{'ready  ' if found else 'MISSING'} {wanted.rsplit('/', 1)[-1]}")
    missing += not found
print("All voter models are on the server." if not missing else
      "Download the missing models in Msty Studio (docs/REPRODUCE.md, step 4).")
'@
$check | & $venvPython -

Write-Host ""
Write-Host "Setup finished." -ForegroundColor Green
Write-Host "Next: .\.venv\Scripts\python.exe -m integrations.mcp.voter_check   (loads each voter model once)"
Write-Host "Then: .\boot.bat   (desktop window)   or   .\.venv\Scripts\python.exe consensus_war_room_genesis.py --no-boot ""Your proposal"""
