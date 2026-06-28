#requires -Version 5.1
param(
    [string[]]$Path
)

$ErrorActionPreference = "Stop"

if (-not $Path -or $Path.Count -eq 0) {
    $Path = @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter "*.ps1" -File | ForEach-Object { $_.FullName })
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

if ($failed) {
    exit 1
}

Write-Host "PowerShell syntax check passed for $($Path.Count) file(s)."
exit 0
