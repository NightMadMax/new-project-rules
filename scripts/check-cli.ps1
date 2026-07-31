#requires -Version 5.1
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Tools = @()
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/Find-Python.ps1")

$Python = Find-Python39
if ($null -eq $Python) {
    Write-Host "Python 3.9+ is required to discover the command-line tools."
    exit 1
}

$Discovery = Join-Path $PSScriptRoot "cli_discovery.py"
& $Python.Source @($Discovery) @Tools
exit $LASTEXITCODE
