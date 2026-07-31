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
. (Join-Path $PSScriptRoot "lib/Find-Python.ps1")

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
