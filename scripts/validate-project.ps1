#requires -Version 5.1
param(
    [string]$Root = ".",

    [ValidateSet("auto", "rules", "project")]
    [string]$Kind = "auto",

    [ValidateSet("auto", "minimal", "software", "operated", "all")]
    [string]$Profile = "auto",

    [switch]$Doctor,
    [switch]$ReportOnly
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/Find-Python.ps1")
$Python = Find-Python39
if ($null -eq $Python) {
    Write-Host "Python 3.9+ is required for project validation."
    exit 1
}

$Validator = Join-Path $PSScriptRoot "validate-project.py"
$Arguments = @($Validator, "--root", $Root, "--kind", $Kind, "--profile", $Profile)
if ($Doctor) { $Arguments += "--doctor" }
if ($ReportOnly) { $Arguments += "--report-only" }

& $Python.Source @Arguments
exit $LASTEXITCODE
