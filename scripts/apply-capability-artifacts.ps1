#requires -Version 5.1
param(
    [Parameter(Mandatory = $true)][string]$Project,
    [Parameter(Mandatory = $true)][string]$Capability,
    [string]$ContractRoot,
    [switch]$Apply,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/Find-Python.ps1")

$Python = Find-Python39
if ($null -eq $Python) {
    Write-Error "Python 3.9+ is required to plan capability artifacts."
    exit 1
}

$Script = Join-Path $PSScriptRoot "apply-capability-artifacts.py"
$Arguments = @($Script, "--project", $Project, "--capability", $Capability)
if ($ContractRoot) { $Arguments += @("--contract-root", $ContractRoot) }
if ($Apply) { $Arguments += "--apply" }
if ($Yes) { $Arguments += "--yes" }

& $Python.Source @Arguments
exit $LASTEXITCODE
