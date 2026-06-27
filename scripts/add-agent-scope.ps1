param(
    [Parameter(Mandatory = $true)]
    [string]$Directory
)

$ErrorActionPreference = "Stop"

# Add directory-scoped agent rules. Keep shared rules in the root AGENTS.md;
# use this only when a subdirectory genuinely needs its own rules. Creates
# <dir>/AGENTS.md (the rules) and <dir>/CLAUDE.md (a one-line @AGENTS.md import
# so Claude Code reads the same scoped file). Safe to re-run.

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

New-Item -ItemType Directory -Force $Directory | Out-Null
$Directory = (Resolve-Path $Directory).Path
$Agents = Join-Path $Directory "AGENTS.md"
$Claude = Join-Path $Directory "CLAUDE.md"

if (-not (Test-Path $Agents)) {
    $stub = @(
        "# Agent Instructions"
        ""
        "Scope-specific rules for this directory. Shared rules stay in the root"
        "``AGENTS.md``; add here only what differs for this part of the project."
        ""
        "-"
    ) -join "`n"
    Write-Utf8NoBom $Agents ($stub + "`n")
    Write-Host "Created $Agents"
}
else {
    Write-Host "Kept existing $Agents (not overwritten)."
}

$item = Get-Item -LiteralPath $Claude -ErrorAction SilentlyContinue
if ($null -ne $item -and $item.LinkType -eq "SymbolicLink") {
    Remove-Item -LiteralPath $Claude
    Write-Utf8NoBom $Claude "@AGENTS.md`n"
    Write-Host "Replaced symlink $Claude with an @import."
}
elseif (-not (Test-Path $Claude)) {
    Write-Utf8NoBom $Claude "@AGENTS.md`n"
    Write-Host "Wrote $Claude (@AGENTS.md)."
}
elseif ((Get-Content -Raw $Claude).Contains("@AGENTS.md")) {
    Write-Host "Already configured: $Claude imports AGENTS.md."
}
else {
    Write-Warning "Conflict: $Claude exists without '@AGENTS.md'. Merge manually."
    exit 1
}
