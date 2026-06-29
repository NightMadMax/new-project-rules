#requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("project", "global")]
    [string]$Target,

    [string]$Root = ".",
    [string]$HomeDirectory = $HOME,

    [ValidateSet("auto", "minimal", "software", "operated", "all")]
    [string]$Profile = "auto",

    [switch]$Plan,
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

if (-not $Plan) {
    Write-Host "Specify -Plan. Mutation is not available in this stage."
    exit 2
}
$Python = Find-Python39
if ($null -eq $Python) {
    Write-Host "Python 3.9+ is required for migration planning."
    exit 1
}
$Arguments = @((Join-Path $PSScriptRoot "plan_migration.py"), "--plan", "--target", $Target, "--root", $Root, "--home", $HomeDirectory, "--profile", $Profile)
if ($ReportOnly) { $Arguments += "--report-only" }
& $Python.Source @Arguments
exit $LASTEXITCODE
