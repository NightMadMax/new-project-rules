#requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [string]$Root,

    [ValidateSet("auto", "adopt-in-place", "re-bootstrap-from-existing")]
    [string]$Strategy = "auto",

    [ValidateSet("auto", "minimal", "software", "operated", "all")]
    [string]$Profile = "auto",

    [switch]$PlanAdopt,
    [switch]$PlanRebootstrap,
    [switch]$Apply,
    [string]$Destination,
    [string]$ProjectName,
    [string]$Fingerprint,
    [switch]$Confirm,
    [switch]$Json
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
    Write-Host "Python 3.9+ is required for existing-project standardization planning."
    exit 1
}

$Arguments = @(
    (Join-Path $PSScriptRoot "standardize_existing_project.py"),
    "--root", $Root,
    "--strategy", $Strategy,
    "--profile", $Profile
)
if ($PlanAdopt) { $Arguments += "--plan-adopt" }
if ($PlanRebootstrap) { $Arguments += "--plan-rebootstrap" }
if ($Apply) { $Arguments += "--apply" }
if ($Destination) { $Arguments += @("--destination", $Destination) }
if ($ProjectName) { $Arguments += @("--project-name", $ProjectName) }
if ($Fingerprint) { $Arguments += @("--fingerprint", $Fingerprint) }
if ($Confirm) { $Arguments += "--yes" }
if ($Json) { $Arguments += "--json" }

& $Python.Source @Arguments
exit $LASTEXITCODE
