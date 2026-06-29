param(
    [Parameter(Mandatory = $true)]
    [string]$Directory,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Rule
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

function Append-Utf8NoBom {
    param([string]$Path, [string]$Line)
    [System.IO.File]::AppendAllText($Path, $Line + "`n", $Utf8NoBom)
}

if (($Directory -split '[\\/]' | Where-Object { $_ -eq '..' }).Count -gt 0) {
    throw "Scope directory must not contain '..' path components."
}
$DirectoryFullPath = [System.IO.Path]::GetFullPath($Directory)
$Probe = $DirectoryFullPath
while (-not (Test-Path -LiteralPath $Probe -PathType Container)) {
    $Parent = Split-Path -Parent $Probe
    if ($Parent -eq $Probe -or [string]::IsNullOrEmpty($Parent)) {
        throw "Cannot locate an existing parent for $Directory."
    }
    $Probe = $Parent
}

$ProjectRoot = (& git -C $Probe rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($ProjectRoot)) {
    throw "Directory must be inside a git project."
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot.Trim())
$runningOnWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
$comparison = if ($runningOnWindows) {
    [System.StringComparison]::OrdinalIgnoreCase
}
else {
    [System.StringComparison]::Ordinal
}
$ProjectPrefix = $ProjectRoot.TrimEnd([char[]]@('\', '/')) + [System.IO.Path]::DirectorySeparatorChar
if (-not $DirectoryFullPath.StartsWith($ProjectPrefix, $comparison)) {
    throw "Scope directory must be below the project root: $ProjectRoot"
}
$RelativeDirectory = $DirectoryFullPath.Substring($ProjectPrefix.Length).Replace('\', '/').TrimEnd('/')
if ([string]::IsNullOrWhiteSpace($RelativeDirectory)) {
    throw "Scope directory must be below the project root: $ProjectRoot"
}
$IndexFile = Join-Path $ProjectRoot "INDEX.md"
if (-not (Test-Path -LiteralPath $IndexFile -PathType Leaf)) {
    throw "Project index not found: $IndexFile"
}

New-Item -ItemType Directory -Force $DirectoryFullPath | Out-Null
$Directory = (Resolve-Path $DirectoryFullPath).Path
$Agents = Join-Path $Directory "AGENTS.md"
$Claude = Join-Path $Directory "CLAUDE.md"

# Validate the Claude bridge before creating or changing any project files.
$item = Get-Item -LiteralPath $Claude -ErrorAction SilentlyContinue
if ($null -ne $item -and $item.LinkType -eq "SymbolicLink") {
    $linkTarget = [string]$item.Target
    if (-not [System.IO.Path]::IsPathRooted($linkTarget)) {
        $linkTarget = Join-Path $Directory $linkTarget
    }
    $normalizedTarget = [System.IO.Path]::GetFullPath($linkTarget)
    $normalizedExpected = [System.IO.Path]::GetFullPath($Agents)
    if (-not $normalizedTarget.Equals($normalizedExpected, $comparison)) {
        throw "$Claude is a symlink to '$($item.Target)', not $Agents. Nothing was changed."
    }
    $ClaudeAction = "migrate"
}
elseif (-not (Test-Path $Claude)) {
    $ClaudeAction = "create"
}
else {
    $content = Get-Content -Raw $Claude
    $normalizedContent = $content -replace "(\r?\n)+$", ""
    if ($normalizedContent -ceq "@AGENTS.md") {
        $ClaudeAction = "keep"
    }
    else {
        throw "$Claude is not the exact one-line import '@AGENTS.md'. Nothing was changed."
    }
}

if (-not (Test-Path $Agents)) {
    $stub = @(
        "# Agent Instructions"
        ""
        "Scope-specific rules for this directory. Shared rules stay in the root"
        "``AGENTS.md``; add here only what differs for this part of the project."
        ""
        "- $Rule"
    ) -join "`n"
    Write-Utf8NoBom $Agents ($stub + "`n")
    Write-Host "Created $Agents"
}
else {
    Write-Host "Kept existing $Agents (not overwritten)."
}

switch ($ClaudeAction) {
    "migrate" {
        Remove-Item -LiteralPath $Claude
        Write-Utf8NoBom $Claude "@AGENTS.md`n"
        Write-Host "Replaced the scoped AGENTS symlink with an @import."
    }
    "create" {
        Write-Utf8NoBom $Claude "@AGENTS.md`n"
        Write-Host "Wrote $Claude (@AGENTS.md)."
    }
    "keep" {
        Write-Host "Already configured: $Claude imports AGENTS.md."
    }
}

$AgentsLink = "[[$RelativeDirectory/AGENTS|$RelativeDirectory/AGENTS.md]]"
$ClaudeLink = "[[$RelativeDirectory/CLAUDE|$RelativeDirectory/CLAUDE.md]]"
$IndexContent = Get-Content -Raw $IndexFile
if (-not $IndexContent.Contains($AgentsLink)) {
    Append-Utf8NoBom $IndexFile "| $AgentsLink | Scoped agent rules |"
}
if (-not $IndexContent.Contains($ClaudeLink)) {
    Append-Utf8NoBom $IndexFile "| $ClaudeLink | Imports scoped AGENTS for Claude Code |"
}

Write-Host "Updated $IndexFile with scoped instruction links."
