#requires -Version 5.1
param(
    [string]$Root = ".",
    [switch]$Write,

    [ValidateSet("all", "claude", "codex")]
    [string]$Client = "all"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/Find-Python.ps1")
$Python = Find-Python39
if ($null -eq $Python) {
    Write-Host "Python 3.9+ is required to render the 1C client projections."
    exit 1
}

$Renderer = Join-Path $PSScriptRoot "render-1c-clients.py"
$Arguments = @($Renderer, "--root", $Root, "--client", $Client)
if ($Write) { $Arguments += "--write" }

& $Python.Source @Arguments
exit $LASTEXITCODE
