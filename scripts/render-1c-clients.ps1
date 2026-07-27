#requires -Version 5.1
param(
    [string]$Root = ".",
    [switch]$Write,

    [ValidateSet("all", "claude", "codex")]
    [string]$Client = "all"
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
    Write-Host "Python 3.9+ is required to render the 1C client projections."
    exit 1
}

$Renderer = Join-Path $PSScriptRoot "render-1c-clients.py"
$Arguments = @($Renderer, "--root", $Root, "--client", $Client)
if ($Write) { $Arguments += "--write" }

& $Python.Source @Arguments
exit $LASTEXITCODE
