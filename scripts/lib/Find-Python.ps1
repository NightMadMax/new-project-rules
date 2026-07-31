#requires -Version 5.1
# One definition of "a usable Python", dot-sourced by every PowerShell wrapper.
#
# It used to be copied into ten of them, and every copy carried the same two
# faults. It took the first `python` on PATH, which on Windows is routinely the
# zero-byte App Execution Alias, so the working interpreter further along the
# same PATH was never reached — the wrapper announced "Python 3.9+ is required"
# on a machine that has it. And it started candidates without guarding the call,
# so a native command that merely writes to stderr became a terminating error
# under `$ErrorActionPreference = "Stop"`, and a file the operating system
# refuses to run threw instead of being skipped.
#
# The canonical implementation, including the install locations outside PATH, is
# scripts/cli_discovery.py — which cannot be used here, because finding Python is
# what this file exists to do.

function Test-PythonCandidate {
    <#
        .SYNOPSIS
        Whether this exact interpreter starts and is new enough.
    #>
    param([Parameter(Mandatory = $true)][string]$Path)

    $Previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    # A stale exit code would otherwise speak for a call that never happened.
    $global:LASTEXITCODE = $null
    try { & $Path -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" *> $null }
    catch { return $false }
    finally { $ErrorActionPreference = $Previous }
    return $LASTEXITCODE -eq 0
}

function Find-Python39 {
    <#
        .SYNOPSIS
        The first interpreter on PATH that actually answers, or $null.
    #>
    foreach ($Name in @("python", "python3")) {
        foreach ($Command in @(Get-Command $Name -CommandType Application -All -ErrorAction SilentlyContinue)) {
            $Item = Get-Item -LiteralPath $Command.Source -ErrorAction SilentlyContinue
            # Never started: launching an alias stub opens the Store instead of
            # answering, and the answer we would get is not about Python.
            if ($null -eq $Item -or $Item.Length -eq 0) { continue }
            if (Test-PythonCandidate $Command.Source) { return $Command }
        }
    }
    $null
}
