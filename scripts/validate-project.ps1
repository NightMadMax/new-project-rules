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
    Write-Host "Python 3.9+ is required for project validation."
    exit 1
}

$Validator = Join-Path $PSScriptRoot "validate-project.py"
$Arguments = @($Validator, "--root", $Root, "--kind", $Kind, "--profile", $Profile)
if ($Doctor) { $Arguments += "--doctor" }
if ($ReportOnly) { $Arguments += "--report-only" }

& $Python.Source @Arguments
exit $LASTEXITCODE
