#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateRange(15, 3600)]
    [int]$IntervalSeconds = 30,

    [ValidateRange(1, 20)]
    [int]$ApiFailureThreshold = 4,

    [Alias("EnsureGo")]
    [switch]$EnsureClaw,
    [switch]$Once
)

$ErrorActionPreference = "Stop"

$MstyStudioExe = "G:\Msty\MstyStudio\MstyStudio.exe"
$MstyGoExe = "G:\Msty\Msty Go\MstyGo.exe"
$ProviderRepairScript = "G:\Msty\keep-msty-running.ps1"
$VibeCliProxyExe = Join-Path $env:APPDATA "MstyStudio\vibe-cli-proxy\msty-cli-proxy-studio.exe"
$VibeCliProxyConfig = Join-Path $env:APPDATA "MstyStudio\vibe-cli-proxy\config.yaml"
$MstyGoModelsUrl = "http://127.0.0.1:11964/v1/models"
$LlamaModelsUrl = "http://127.0.0.1:11454/v1/models"
$VibeCliProxyModelsUrl = "http://127.0.0.1:8317/v1/models"
$LogDirectory = "G:\Msty\logs"
$LogPath = Join-Path $LogDirectory "msty-background-watchdog.log"
$MutexName = "Local\MstyBackgroundWatchdog"

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null

function Write-WatchdogLog {
    param([Parameter(Mandatory)][string]$Message)

    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Get-ManagedProcess {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$ExpectedPath
    )

    return @(
        Get-Process -Name $Name -ErrorAction SilentlyContinue |
            Where-Object {
                try {
                    [string]::Equals($_.Path, $ExpectedPath, [System.StringComparison]::OrdinalIgnoreCase)
                } catch {
                    $false
                }
            }
    )
}

function Start-ManagedApplication {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string]$Label,
        [ValidateSet("Hidden", "Minimized", "Normal")][string]$WindowStyle
    )

    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) {
        throw "Missing $Label executable: $FilePath"
    }

    Start-Process `
        -FilePath $FilePath `
        -WorkingDirectory (Split-Path -Parent $FilePath) `
        -WindowStyle $WindowStyle | Out-Null
    Write-WatchdogLog "STARTED label=$Label path=$FilePath window=$WindowStyle"
}

function Start-VibeCliProxy {
    if (-not (Test-Path -LiteralPath $VibeCliProxyExe -PathType Leaf)) {
        throw "Missing Vibe CLI proxy executable: $VibeCliProxyExe"
    }
    if (-not (Test-Path -LiteralPath $VibeCliProxyConfig -PathType Leaf)) {
        throw "Missing Vibe CLI proxy configuration: $VibeCliProxyConfig"
    }

    Start-Process `
        -FilePath $VibeCliProxyExe `
        -ArgumentList @("--config", $VibeCliProxyConfig) `
        -WorkingDirectory (Split-Path -Parent $VibeCliProxyExe) `
        -WindowStyle Hidden | Out-Null
    Write-WatchdogLog "STARTED label=VibeCliProxy path=$VibeCliProxyExe window=Hidden"
}

function Restart-VibeCliProxy {
    Write-WatchdogLog "VIBE_PROXY_REPAIR_STARTED failures=$script:ConsecutiveVibeProxyFailures url=$VibeCliProxyModelsUrl"

    $proxyProcesses = Get-ManagedProcess -Name "msty-cli-proxy-studio" -ExpectedPath $VibeCliProxyExe
    foreach ($proxyProcess in $proxyProcesses) {
        Stop-Process -Id $proxyProcess.Id -Force -ErrorAction Stop
        Write-WatchdogLog "VIBE_PROXY_STOPPED pid=$($proxyProcess.Id)"
    }

    Start-VibeCliProxy
    Write-WatchdogLog "VIBE_PROXY_REPAIR_FINISHED"
}

function Test-MstyProvider {
    param([Parameter(Mandatory)][string]$Url)

    try {
        $response = Invoke-RestMethod -Uri $Url -TimeoutSec 5
        return $null -ne $response.data -and @($response.data).Count -gt 0
    } catch {
        return $false
    }
}

function Repair-MstyProvider {
    if (-not (Test-Path -LiteralPath $ProviderRepairScript -PathType Leaf)) {
        throw "Missing provider repair script: $ProviderRepairScript"
    }

    Write-WatchdogLog "PROVIDER_REPAIR_STARTED msty_local_ai_failures=$script:ConsecutiveMstyGoApiFailures llama_failures=$script:ConsecutiveLlamaApiFailures"
    & powershell.exe `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -WindowStyle Hidden `
        -File $ProviderRepairScript `
        -WindowMode Hidden 2>&1 |
        ForEach-Object { Write-WatchdogLog "PROVIDER_REPAIR_OUTPUT $_" }

    if ($LASTEXITCODE -ne 0) {
        throw "Provider repair exited with code $LASTEXITCODE"
    }

    Write-WatchdogLog "PROVIDER_REPAIR_FINISHED"
}

$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, $MutexName, [ref]$createdNew)
if (-not $createdNew) {
    Write-WatchdogLog "DUPLICATE_WATCHDOG_EXIT"
    $mutex.Dispose()
    exit 0
}

$script:ConsecutiveMstyGoApiFailures = 0
$script:ConsecutiveLlamaApiFailures = 0
$script:ConsecutiveVibeProxyFailures = 0
$goStartupChecked = $false

try {
    Write-WatchdogLog "WATCHDOG_STARTED interval_seconds=$IntervalSeconds api_failure_threshold=$ApiFailureThreshold ensure_claw=$EnsureClaw once=$Once"

    while ($true) {
        try {
            if ((Get-ManagedProcess -Name "MstyStudio" -ExpectedPath $MstyStudioExe).Count -eq 0) {
                Start-ManagedApplication -FilePath $MstyStudioExe -Label "MstyStudio" -WindowStyle Minimized
                $script:ConsecutiveMstyGoApiFailures = 0
                $script:ConsecutiveLlamaApiFailures = 0
            }

            if ($EnsureClaw -and -not $goStartupChecked) {
                if ((Get-ManagedProcess -Name "MstyGo" -ExpectedPath $MstyGoExe).Count -eq 0) {
                    Start-ManagedApplication -FilePath $MstyGoExe -Label "MstyGo" -WindowStyle Minimized
                } else {
                    Write-WatchdogLog "MSTY_GO_ALREADY_RUNNING"
                }
                $goStartupChecked = $true
            }

            if (Test-MstyProvider -Url $MstyGoModelsUrl) {
                if ($script:ConsecutiveMstyGoApiFailures -gt 0) {
                    Write-WatchdogLog "PROVIDER_RECOVERED service=msty-local-ai previous_failures=$script:ConsecutiveMstyGoApiFailures url=$MstyGoModelsUrl"
                }
                $script:ConsecutiveMstyGoApiFailures = 0
            } else {
                $script:ConsecutiveMstyGoApiFailures++
                Write-WatchdogLog "PROVIDER_UNAVAILABLE service=msty-local-ai consecutive_failures=$script:ConsecutiveMstyGoApiFailures url=$MstyGoModelsUrl"
            }

            if (Test-MstyProvider -Url $LlamaModelsUrl) {
                if ($script:ConsecutiveLlamaApiFailures -gt 0) {
                    Write-WatchdogLog "PROVIDER_RECOVERED service=llama-cpp previous_failures=$script:ConsecutiveLlamaApiFailures url=$LlamaModelsUrl"
                }
                $script:ConsecutiveLlamaApiFailures = 0
            } else {
                $script:ConsecutiveLlamaApiFailures++
                Write-WatchdogLog "PROVIDER_UNAVAILABLE service=llama-cpp consecutive_failures=$script:ConsecutiveLlamaApiFailures url=$LlamaModelsUrl"
            }

            if (
                $script:ConsecutiveMstyGoApiFailures -ge $ApiFailureThreshold -or
                $script:ConsecutiveLlamaApiFailures -ge $ApiFailureThreshold
            ) {
                Repair-MstyProvider
                $script:ConsecutiveMstyGoApiFailures = 0
                $script:ConsecutiveLlamaApiFailures = 0
            }

            if (Test-MstyProvider -Url $VibeCliProxyModelsUrl) {
                if ($script:ConsecutiveVibeProxyFailures -gt 0) {
                    Write-WatchdogLog "PROVIDER_RECOVERED service=vibe-cli-proxy previous_failures=$script:ConsecutiveVibeProxyFailures url=$VibeCliProxyModelsUrl"
                }
                $script:ConsecutiveVibeProxyFailures = 0
            } else {
                $script:ConsecutiveVibeProxyFailures++
                Write-WatchdogLog "PROVIDER_UNAVAILABLE service=vibe-cli-proxy consecutive_failures=$script:ConsecutiveVibeProxyFailures url=$VibeCliProxyModelsUrl"

                $proxyProcessCount = (Get-ManagedProcess -Name "msty-cli-proxy-studio" -ExpectedPath $VibeCliProxyExe).Count
                if ($proxyProcessCount -eq 0) {
                    Write-WatchdogLog "VIBE_PROXY_PROCESS_MISSING"
                    Start-VibeCliProxy
                    $script:ConsecutiveVibeProxyFailures = 0
                } elseif ($script:ConsecutiveVibeProxyFailures -ge $ApiFailureThreshold) {
                    Restart-VibeCliProxy
                    $script:ConsecutiveVibeProxyFailures = 0
                }
            }
        } catch {
            Write-WatchdogLog "CHECK_ERROR $($_.Exception.Message)"
        }

        if ($Once) {
            break
        }
        Start-Sleep -Seconds $IntervalSeconds
    }
} finally {
    Write-WatchdogLog "WATCHDOG_STOPPED"
    try {
        $mutex.ReleaseMutex()
    } catch {
    }
    $mutex.Dispose()
}
