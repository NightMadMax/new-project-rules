#requires -Version 5.1
param(
    [string[]]$Path
)

$ErrorActionPreference = "Stop"

if (-not $Path -or $Path.Count -eq 0) {
    # Our own wrappers and the payload we ship. Checking only scripts/ left the
    # sixty vendored .ps1 unparsed — the files a created project actually runs,
    # and the ones nobody here would notice breaking. A vendored parse error is
    # still an error: it means the release delivers a script that cannot run.
    $roots = @(
        $PSScriptRoot,
        (Join-Path (Split-Path -Parent $PSScriptRoot) "templates")
    )
    $Path = @(
        foreach ($root in $roots) {
            if (Test-Path -LiteralPath $root) {
                # -Force: the payload lives under .agents, and Get-ChildItem
                # skips dot-directories without it — which is how sixty files
                # stayed unparsed while the check reported success.
                Get-ChildItem -LiteralPath $root -Filter "*.ps1" -File -Recurse -Force |
                    ForEach-Object { $_.FullName }
            }
        }
    )
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
