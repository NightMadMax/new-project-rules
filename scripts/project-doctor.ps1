#requires -Version 5.1
param(
    [string]$Root = ".",

    [ValidateSet("codex", "claude", "both")]
    [string]$AgentMode = "both",

    [ValidateSet("auto", "minimal", "software", "operated", "all")]
    [string]$Profile = "auto",

    [switch]$ReportOnly
)

$ErrorActionPreference = "Stop"
$CheckEnvironment = Join-Path $PSScriptRoot "check-environment.ps1"
$Validator = Join-Path $PSScriptRoot "validate-project.py"
$Engine = (Get-Process -Id $PID).Path

Write-Host "Environment diagnostics:"
& $Engine -NoProfile -File $CheckEnvironment -AgentMode $AgentMode
$EnvironmentExit = $LASTEXITCODE

Write-Host ""
Write-Host "Project diagnostics:"
function Find-Python39 {
    foreach ($Name in @("python", "python3")) {
        $Command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $Command) {
            & $Command.Source -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" *> $null
            if ($LASTEXITCODE -eq 0) { return $Command }
        }
    }
    $null
}
$Python = Find-Python39
if ($null -eq $Python) {
    Write-Host "[WARN] validator.runtime: Python 3.9+ is unavailable; structural validation was skipped."
    $ValidatorExit = 0
}
else {
    $Arguments = @($Validator, "--root", $Root, "--kind", "auto", "--profile", $Profile, "--doctor")
    if ($ReportOnly) { $Arguments += "--report-only" }
    & $Python.Source @Arguments
    $ValidatorExit = $LASTEXITCODE
}

if ($ReportOnly) { exit 0 }
if ($ValidatorExit -eq 2) { exit 2 }
if ($EnvironmentExit -ne 0 -or $ValidatorExit -ne 0) { exit 1 }
exit 0
