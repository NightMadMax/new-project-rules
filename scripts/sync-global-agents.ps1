#requires -Version 5.1
param(
    [Parameter(Mandatory = $true, ParameterSetName = "Check")]
    [switch]$Check,

    [Parameter(Mandatory = $true, ParameterSetName = "Diff")]
    [switch]$Diff,

    [string]$HomeDirectory = $HOME,
    [switch]$ReportOnly
)

$ErrorActionPreference = "Stop"
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
    Write-Host "Python 3.9+ is required for global policy sync inspection."
    exit 1
}
$Arguments = @((Join-Path $PSScriptRoot "sync_global_agents.py"), "--home", $HomeDirectory)
if ($Check) { $Arguments += "--check" } else { $Arguments += "--diff" }
if ($ReportOnly) { $Arguments += "--report-only" }
& $Python.Source @Arguments
exit $LASTEXITCODE
