#requires -Version 5.1
param(
    [string[]]$Path,

    # The ~60 vendored .ps1 under templates/**/upstream/** are delivered into
    # every project with capability 1c and were parsed by nothing: the checker
    # looked only at scripts/. They are byte-exact upstream payload, so a parse
    # error in them is not ours to fix — it is ours to know about before it
    # reaches a user's machine, which is why this is a separate report-only run.
    [switch]$Delivered
)

$ErrorActionPreference = "Stop"

if (-not $Path -or $Path.Count -eq 0) {
    if ($Delivered) {
        $templates = Join-Path (Split-Path -Parent $PSScriptRoot) "templates"
        $Path = @(Get-ChildItem -LiteralPath $templates -Filter "*.ps1" -File -Recurse |
            ForEach-Object { $_.FullName })
    }
    else {
        $Path = @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter "*.ps1" -File |
            ForEach-Object { $_.FullName })
    }
}

if ($Path.Count -eq 0) {
    Write-Host "No PowerShell files to check."
    exit 0
}

$failed = $false
foreach ($candidate in $Path) {
    $resolved = Resolve-Path -LiteralPath $candidate -ErrorAction Stop
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $resolved.Path,
        [ref]$tokens,
        [ref]$errors
    )
    foreach ($parseError in $errors) {
        $failed = $true
        $position = $parseError.Extent.StartScriptPosition
        Write-Host ("{0}:{1}:{2}: {3}" -f $resolved.Path, $position.LineNumber, $position.ColumnNumber, $parseError.Message)
    }
}

if ($failed -and $Delivered) {
    # Report-only: the payload is byte-exact and cannot be edited here, so a
    # red build would only teach people to ignore this run.
    Write-Host "Delivered payload has parse errors; the payload is byte-exact upstream and is not edited here."
    exit 0
}

if ($failed) {
    exit 1
}

Write-Host "PowerShell syntax check passed for $($Path.Count) file(s)."
exit 0
