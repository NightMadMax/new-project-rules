#requires -Version 5.1
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Tools = @()
)

$ErrorActionPreference = "Stop"

function Find-Python39 {
    # -All, not the first hit: on Windows the first `python` on PATH is often
    # the zero-byte App Execution Alias, and the working interpreter sits behind
    # it. A zero-length file is never started — it opens the Store instead of
    # answering.
    foreach ($Name in @("python", "python3")) {
        $Commands = @(Get-Command $Name -CommandType Application -All -ErrorAction SilentlyContinue)
        foreach ($Command in $Commands) {
            if ((Get-Item $Command.Source).Length -eq 0) { continue }
            & $Command.Source -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" *> $null
            if ($LASTEXITCODE -eq 0) { return $Command }
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
