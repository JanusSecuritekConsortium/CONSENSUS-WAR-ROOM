param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Exe = Join-Path $Root "MstyConsensusLauncher.exe"
$Config = Join-Path $Root "launcher.config.json"
$Backup = Join-Path $Root ("launcher.config.backup-" + (Get-Date -Format "yyyyMMddHHmmss") + ".json")

function Invoke-Launcher {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Arguments,
        [int[]]$AllowedExitCodes = @(0)
    )

    $process = Start-Process -FilePath $Exe -ArgumentList $Arguments -Wait -PassThru
    $exitCode = $process.ExitCode
    Write-Output "$Arguments -> exit $exitCode"
    if ($AllowedExitCodes -notcontains $exitCode) {
        throw "Unexpected exit code $exitCode for $Arguments"
    }
}

Copy-Item -LiteralPath $Config -Destination $Backup -Force
try {
    Invoke-Launcher "--self-test"
    Invoke-Launcher "--status --json"
    Invoke-Launcher "--diagnose-api" @(0, 1)
    Invoke-Launcher "--diagnose-port"
    Invoke-Launcher "--print-config --json"

    $json = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
    $json.fallback_msty_api_urls = @("not-a-valid-url")
    $json.allow_fallback_api = $true
    $json | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Config -Encoding UTF8
    Invoke-Launcher "--self-test" @(1)

    $json.allow_fallback_api = $false
    $json | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Config -Encoding UTF8
    Invoke-Launcher "--self-test"

    Copy-Item -LiteralPath $Backup -Destination $Config -Force
    $json = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
    $json.consensus_environment_variables = @("malformed")
    $json | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Config -Encoding UTF8
    Invoke-Launcher "--self-test" @(1)

    Write-Output "Regression checks passed."
}
finally {
    Copy-Item -LiteralPath $Backup -Destination $Config -Force
    Remove-Item -LiteralPath $Backup -Force -ErrorAction SilentlyContinue
}
