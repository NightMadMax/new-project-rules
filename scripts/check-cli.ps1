#requires -Version 5.1
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Tools = @()
)

$ErrorActionPreference = "Stop"

function Test-Python39 {
    # Every way a candidate can fail is an answer about that candidate, never a
    # reason to stop looking: under $ErrorActionPreference = "Stop" a native
    # command that merely writes to stderr becomes a terminating error, and a
    # file the OS refuses to run throws outright. A stale $LASTEXITCODE would
    # otherwise speak for a call that never happened.
    param([string]$Path)
    $Previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $global:LASTEXITCODE = $null
    try { & $Path -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" *> $null }
    catch { return $false }
    finally { $ErrorActionPreference = $Previous }
    return $LASTEXITCODE -eq 0
}

function Find-Python39 {
    # -All, not the first hit: on Windows the first `python` on PATH is often
    # the zero-byte App Execution Alias, and the working interpreter sits behind
    # it. A zero-length file is never started - it opens the Store instead of
    # answering.
    foreach ($Name in @("python", "python3")) {
        foreach ($Command in @(Get-Command $Name -CommandType Application -All -ErrorAction SilentlyContinue)) {
            $Item = Get-Item $Command.Source -ErrorAction SilentlyContinue
            if ($null -eq $Item -or $Item.Length -eq 0) { continue }
            if (Test-Python39 $Command.Source) { return $Command }
        }
    }
    $null
}

$Python = Find-Python39
if ($null -eq $Python) {
    Write-Host "Python 3.9+ is required to discover the command-line tools."
    exit 1
}

$Discovery = Join-Path $PSScriptRoot "cli_discovery.py"
& $Python.Source @($Discovery) @Tools
exit $LASTEXITCODE
