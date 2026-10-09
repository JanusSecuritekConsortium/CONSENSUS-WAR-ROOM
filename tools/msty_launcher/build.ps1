param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source = Join-Path $Root "MstyConsensusLauncher.cs"
$Output = Join-Path $Root "MstyConsensusLauncher.exe"
$Icon = "G:\CONSENSUS_SYSTEM\static\icons\consensus_icon.ico"

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Missing source: $Source"
}

$references = @(
    "System.dll",
    "System.Core.dll",
    "System.Web.Extensions.dll",
    "System.Windows.Forms.dll"
)

$compilerOptions = "/target:winexe /platform:anycpu"
if (Test-Path -LiteralPath $Icon) {
    $compilerOptions = "$compilerOptions /win32icon:`"$Icon`""
}

$compilerParameters = New-Object System.CodeDom.Compiler.CompilerParameters
$compilerParameters.CompilerOptions = $compilerOptions
$compilerParameters.OutputAssembly = $Output
$compilerParameters.GenerateExecutable = $true
$compilerParameters.GenerateInMemory = $false
[void]$compilerParameters.ReferencedAssemblies.AddRange($references)

Add-Type `
    -TypeDefinition (Get-Content -LiteralPath $Source -Raw) `
    -CompilerParameters $compilerParameters

if (-not (Test-Path -LiteralPath $Output)) {
    throw "Build did not produce $Output"
}

Get-Item -LiteralPath $Output | Select-Object FullName,Length,LastWriteTime
