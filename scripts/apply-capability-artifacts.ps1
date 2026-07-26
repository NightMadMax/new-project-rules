#requires -Version 5.1
param(
    [Parameter(Mandatory = $true)][string]$Project,
    [Parameter(Mandatory = $true)][string]$Capability,
    [string]$ContractRoot,
    [switch]$Apply,
    [switch]$Yes
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
