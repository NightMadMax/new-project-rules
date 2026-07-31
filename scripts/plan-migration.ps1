#requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("project", "global", "project-agents")]
    [string]$Target,

    [string]$Root = ".",
    [string]$HomeDirectory = $HOME,

    [ValidateSet("auto", "minimal", "software", "operated", "all")]
    [string]$Profile = "auto",

    [switch]$AcceptUnmanagedAsLocal,

    [Parameter(Mandatory = $true, ParameterSetName = "Plan")]
    [switch]$Plan,

    [Parameter(Mandatory = $true, ParameterSetName = "Apply")]
    [switch]$Apply,

    [Parameter(Mandatory = $true, ParameterSetName = "Apply")]
    [string]$Fingerprint,

    [Parameter(Mandatory = $true, ParameterSetName = "Apply")]
    [switch]$Confirm,

    [Parameter(ParameterSetName = "Plan")]
    [switch]$ReportOnly
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/Find-Python.ps1")

$Python = Find-Python39
if ($null -eq $Python) {
    Write-Host "Python 3.9+ is required for migration planning."
    exit 1
}
$Mode = if ($Plan) { "--plan" } else { "--apply" }
$Arguments = @((Join-Path $PSScriptRoot "plan_migration.py"), $Mode, "--target", $Target, "--root", $Root, "--home", $HomeDirectory, "--profile", $Profile)
if ($AcceptUnmanagedAsLocal) { $Arguments += "--accept-unmanaged-as-local" }
if ($ReportOnly) { $Arguments += "--report-only" }
if ($Apply) { $Arguments += @("--fingerprint", $Fingerprint, "--yes") }
& $Python.Source @Arguments
exit $LASTEXITCODE
