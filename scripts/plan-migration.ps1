#requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("project", "global", "project-agents")]
    [string]$Target,

    [string]$Root = ".",
    [string]$HomeDirectory = $HOME,

    [ValidateSet("auto", "minimal", "software", "operated", "all")]
    [string]$Profile = "auto",

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
    Write-Host "Python 3.9+ is required for migration planning."
    exit 1
}
$Mode = if ($Plan) { "--plan" } else { "--apply" }
$Arguments = @((Join-Path $PSScriptRoot "plan_migration.py"), $Mode, "--target", $Target, "--root", $Root, "--home", $HomeDirectory, "--profile", $Profile)
if ($ReportOnly) { $Arguments += "--report-only" }
if ($Apply) { $Arguments += @("--fingerprint", $Fingerprint, "--yes") }
& $Python.Source @Arguments
exit $LASTEXITCODE
