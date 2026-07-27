#requires -Version 5.1
param(
    [string]$Root = ".",

    [Parameter(Mandatory = $true)]
    [string]$Base,

    [string]$Converter = "",

    [string]$ConverterBack = "",

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
$Arguments = @($Exporter, "--root", $Root, "--base", $Base, "--converter", $Converter, "--converter-back", $ConverterBack)
if ($Import) { $Arguments += "--import" }
if ($Apply) { $Arguments += "--apply" }
if ($Release) { $Arguments += "--release" }

& $Python.Source @Arguments
exit $LASTEXITCODE
