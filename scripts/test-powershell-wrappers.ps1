#requires -Version 5.1
# The wrappers claimed to look for a usable Python rather than for a name, and
# nothing checked it. Two reviews later the claim turned out to be false in three
# separate ways, so the claim now has a test: fixtures stand in for the awkward
# candidates Windows actually produces.

$ErrorActionPreference = "Stop"
$Failures = New-Object System.Collections.ArrayList

function Assert-That {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { [void]$Failures.Add($Message) }
}

$Workspace = Join-Path ([System.IO.Path]::GetTempPath()) ("npr-wrappers-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force $Workspace | Out-Null
$OriginalPath = $env:PATH

try {
    . (Join-Path $PSScriptRoot "lib/Find-Python.ps1")

    # A zero-byte executable is the App Execution Alias stub: it resolves like a
    # program and opens the Store instead of answering.
    $stubDirectory = Join-Path $Workspace "stub"
    New-Item -ItemType Directory -Force $stubDirectory | Out-Null
    New-Item -ItemType File -Force (Join-Path $stubDirectory "python.exe") | Out-Null

    # A real interpreter, reached only if the stub does not stop the search.
    $realDirectory = Join-Path $Workspace "real"
    New-Item -ItemType Directory -Force $realDirectory | Out-Null
    $realPython = (Get-Command python -CommandType Application -All -ErrorAction SilentlyContinue |
        Where-Object { (Get-Item -LiteralPath $_.Source).Length -gt 0 } | Select-Object -First 1)
    if ($null -eq $realPython) {
        Write-Host "SKIP: no working Python on this machine to stand behind the stub"
    }
    else {
        # A shim that writes to stderr and still succeeds: under
        # $ErrorActionPreference = "Stop" this used to kill the whole script.
        Set-Content -LiteralPath (Join-Path $realDirectory "python.cmd") -Encoding ASCII -Value @(
            "@echo off",
            "echo deprecation warning 1>&2",
            "`"$($realPython.Source)`" %*"
        )

        $env:PATH = "$stubDirectory;$realDirectory"
        $found = Find-Python39
        Assert-That ($null -ne $found) "the working interpreter behind the stub must be found"
        if ($null -ne $found) {
            Assert-That ((Get-Item -LiteralPath $found.Source).Length -gt 0) `
                "the zero-byte stub must never be chosen"
        }

        # Only the stub: nothing usable, and the search must answer that instead
        # of throwing.
        $env:PATH = $stubDirectory
        $missing = Find-Python39
        Assert-That ($null -eq $missing) "a stub alone must not pass for an interpreter"
    }

    # The helper is dot-sourced, not copied: a second definition would drift.
    $env:PATH = $OriginalPath
    # This file names the function to check for it, so it cannot be its own
    # counterexample.
    $scripts = @(Get-ChildItem (Join-Path $PSScriptRoot "*.ps1") |
        Where-Object { $_.FullName -ne $PSCommandPath })
    $copies = @($scripts | Where-Object { (Get-Content -LiteralPath $_.FullName -Raw) -match "function Find-Python39" })
    Assert-That ($copies.Count -eq 0) `
        "Find-Python39 must live only in lib/Find-Python.ps1, found in: $($copies.Name -join ', ')"

    $users = @($scripts | Where-Object { (Get-Content -LiteralPath $_.FullName -Raw) -match "Find-Python39" })
    foreach ($user in $users) {
        $text = Get-Content -LiteralPath $user.FullName -Raw
        Assert-That ($text -match "lib/Find-Python\.ps1") `
            "$($user.Name) calls Find-Python39 without dot-sourcing the helper"
    }
}
finally {
    $env:PATH = $OriginalPath
    Remove-Item -LiteralPath $Workspace -Recurse -Force -ErrorAction SilentlyContinue
}

if ($Failures.Count -gt 0) {
    foreach ($failure in $Failures) { Write-Host "FAIL: $failure" }
    Write-Host "$($Failures.Count) wrapper check(s) failed."
    exit 1
}

Write-Host "PowerShell wrapper checks passed."
