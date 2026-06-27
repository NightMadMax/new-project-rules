$ErrorActionPreference = "Stop"

# Wire global agent instructions for both Codex and Claude Code without
# duplicating content. Codex reads ~/.codex/AGENTS.md; Claude Code reads
# ~/.claude/CLAUDE.md, which here only imports the Codex file. Safe to re-run.

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

$RulesRoot = Split-Path -Parent $PSScriptRoot
$GlobalSrc = Join-Path $RulesRoot "GLOBAL_AGENT_INSTRUCTIONS.md"
$CodexDir = Join-Path $HOME ".codex"
$ClaudeDir = Join-Path $HOME ".claude"
$CodexFile = Join-Path $CodexDir "AGENTS.md"
$ClaudeFile = Join-Path $ClaudeDir "CLAUDE.md"
$ImportLine = "@~/.codex/AGENTS.md"

New-Item -ItemType Directory -Force $CodexDir | Out-Null
New-Item -ItemType Directory -Force $ClaudeDir | Out-Null

# 1. Validate the Claude bridge before creating or changing any files.
$item = Get-Item -LiteralPath $ClaudeFile -ErrorAction SilentlyContinue
if ($null -ne $item -and $item.LinkType -eq "SymbolicLink") {
    $linkTarget = [string]$item.Target
    if (-not [System.IO.Path]::IsPathRooted($linkTarget)) {
        $linkTarget = Join-Path $ClaudeDir $linkTarget
    }
    $normalizedTarget = [System.IO.Path]::GetFullPath($linkTarget)
    $normalizedExpected = [System.IO.Path]::GetFullPath($CodexFile)
    $runningOnWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
    $comparison = if ($runningOnWindows) {
        [System.StringComparison]::OrdinalIgnoreCase
    }
    else {
        [System.StringComparison]::Ordinal
    }
    if (-not $normalizedTarget.Equals($normalizedExpected, $comparison)) {
        throw "$ClaudeFile is a symlink to '$($item.Target)', not $CodexFile. Nothing was changed."
    }
    $ClaudeAction = "migrate"
}
elseif (-not (Test-Path $ClaudeFile)) {
    $ClaudeAction = "create"
}
else {
    $content = Get-Content -Raw $ClaudeFile
    $normalizedContent = $content -replace "(\r?\n)+$", ""
    if ($normalizedContent -ceq $ImportLine) {
        $ClaudeAction = "keep"
    }
    else {
        throw "$ClaudeFile is not the exact one-line import '$ImportLine'. Nothing was changed."
    }
}

# 2. Ensure the canonical Codex global instructions exist; never overwrite.
if (-not (Test-Path $CodexFile)) {
    if (Test-Path $GlobalSrc) {
        $content = Get-Content -Raw -Encoding utf8 $GlobalSrc
        Write-Utf8NoBom $CodexFile $content
        Write-Host "Created $CodexFile from GLOBAL_AGENT_INSTRUCTIONS.md"
    }
    else {
        throw "$CodexFile is missing and GLOBAL_AGENT_INSTRUCTIONS.md was not found. Add your global rules there."
    }
}
else {
    Write-Host "Kept existing $CodexFile (not overwritten)."
}

# 3. Point Claude Code at the same file via a one-line import.
switch ($ClaudeAction) {
    "migrate" {
        Remove-Item -LiteralPath $ClaudeFile
        Write-Utf8NoBom $ClaudeFile "$ImportLine`n"
        Write-Host "Replaced the canonical Codex symlink with an @import."
    }
    "create" {
        Write-Utf8NoBom $ClaudeFile "$ImportLine`n"
        Write-Host "Created $ClaudeFile importing ~/.codex/AGENTS.md."
    }
    "keep" {
        Write-Host "Already configured: $ClaudeFile imports ~/.codex/AGENTS.md."
    }
}

Write-Host "Global agent setup complete."
