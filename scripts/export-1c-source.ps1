#requires -Version 5.1
param(
    [string]$Root = ".",

    [Parameter(Mandatory = $true)]
    [string]$Base,

    [string]$Converter = "",

    [string]$ConverterBack = "",

    [string]$SourceOption = "--source",

    [string]$TargetOption = "--target",

    # The return names the same directories with the other flags: 1cedtcli
    # exports --project into --configuration-files and imports the other way
    # round. Empty means "same as the export" (defect 166).
    [string]$BackSourceOption = "",

    [string]$BackTargetOption = "",

    [switch]$SkipDeterminismCheck,

    [switch]$Import,
    [switch]$Apply,
    [switch]$Release
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
    Write-Host "Python 3.9+ is required to export the 1C source tree."
    exit 1
}

$Exporter = Join-Path $PSScriptRoot "export-1c-source.py"
# Written as "--option=value", and empty values are not passed at all. Two
# reasons, both of which made this wrapper unusable before: Windows PowerShell
# 5.1 drops empty strings from a native command's arguments, so the flag arrived
# without its value; and every option name here starts with a dash, which
# argparse reads as the next flag rather than as a value.
$Arguments = @($Exporter, "--root", $Root, "--base", $Base)
foreach ($Pair in @(
    @("--converter", $Converter),
    @("--converter-back", $ConverterBack),
    @("--source-option", $SourceOption),
    @("--target-option", $TargetOption),
    @("--back-source-option", $BackSourceOption),
    @("--back-target-option", $BackTargetOption)
)) {
    if (-not [string]::IsNullOrEmpty($Pair[1])) { $Arguments += "$($Pair[0])=$($Pair[1])" }
}
if ($SkipDeterminismCheck) { $Arguments += "--skip-determinism-check" }
if ($Import) { $Arguments += "--import" }
if ($Apply) { $Arguments += "--apply" }
if ($Release) { $Arguments += "--release" }

& $Python.Source @Arguments
exit $LASTEXITCODE
