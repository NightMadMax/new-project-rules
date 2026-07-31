#requires -Version 5.1
param(
    [string]$Root = ".",

    [switch]$Apply,
    [string]$Today = "",

    [int]$ChangelogMaxKb = 32,
    [int]$ChangelogTargetKb = 24,
    [int]$ChangelogKeep = 5,
    [int]$FixedMaxAgeDays = 90,
    [int]$StaleDays = 60
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/Find-Python.ps1")
$Python = Find-Python39
if ($null -eq $Python) {
    Write-Host "Python 3.9+ is required for project compression."
    exit 1
}

$Script = Join-Path $PSScriptRoot "compress-project.py"
$Arguments = @(
    $Script, "--root", $Root,
    "--changelog-max-kb", $ChangelogMaxKb,
    "--changelog-target-kb", $ChangelogTargetKb,
    "--changelog-keep", $ChangelogKeep,
    "--fixed-max-age-days", $FixedMaxAgeDays,
    "--stale-days", $StaleDays
)
if ($Apply) { $Arguments += "--apply" }
if ($Today -ne "") { $Arguments += @("--today", $Today) }

& $Python.Source @Arguments
exit $LASTEXITCODE
