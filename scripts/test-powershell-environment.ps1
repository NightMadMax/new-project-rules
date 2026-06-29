#requires -Version 5.1
param([switch]$Quiet)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Names = @(
    "PATH", "HOME", "USERPROFILE", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM",
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
    "MOCK_GIT_FAIL_COMMAND", "REAL_GIT_PATH", "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0"
)

function Snapshot-Environment {
    $result = @{}
    foreach ($Name in $Names) {
        $item = Get-Item -LiteralPath "Env:$Name" -ErrorAction SilentlyContinue
        $result[$Name] = if ($null -eq $item) {
            [pscustomobject]@{ Exists = $false; Value = $null }
        }
        else {
            [pscustomobject]@{ Exists = $true; Value = $item.Value }
        }
    }
    $result
}

$Before = Snapshot-Environment
foreach ($Test in @("test-bootstrap.ps1", "test-contract.ps1")) {
    $Output = @(& (Join-Path $ScriptDir $Test) 2>&1)
    if ($LASTEXITCODE -ne 0) {
        $Output | ForEach-Object { Write-Host $_ }
        Write-Host "FAIL: $Test returned $LASTEXITCODE"
        exit 1
    }
}
$After = Snapshot-Environment
$Failures = 0
foreach ($Name in $Names) {
    if ($Before[$Name].Exists -ne $After[$Name].Exists -or $Before[$Name].Value -cne $After[$Name].Value) {
        Write-Host "FAIL: $Name changed existence or value"
        $Failures++
    }
}
if ($Failures -ne 0) {
    Write-Host "$Failures environment isolation check(s) failed."
    exit 1
}
if (-not $Quiet) { Write-Host "PowerShell test environment isolation passed." }
exit 0
