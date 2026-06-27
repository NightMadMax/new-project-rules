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

# 1. Ensure the canonical Codex global instructions exist; never overwrite.
if (-not (Test-Path $CodexFile)) {
    if (Test-Path $GlobalSrc) {
        $content = Get-Content -Raw -Encoding utf8 $GlobalSrc
        Write-Utf8NoBom $CodexFile $content
        Write-Host "Created $CodexFile from GLOBAL_AGENT_INSTRUCTIONS.md"
    }
    else {
        Write-Warning "$CodexFile is missing and GLOBAL_AGENT_INSTRUCTIONS.md was not found. Add your global rules there."
    }
}
else {
    Write-Host "Kept existing $CodexFile (not overwritten)."
}

# 2. Point Claude Code at the same file via a one-line import.
$item = Get-Item -LiteralPath $ClaudeFile -ErrorAction SilentlyContinue
if ($null -ne $item -and $item.LinkType -eq "SymbolicLink") {
    Remove-Item -LiteralPath $ClaudeFile
    Write-Utf8NoBom $ClaudeFile "$ImportLine`n"
    Write-Host "Replaced symlink $ClaudeFile with an @import."
}
elseif (-not (Test-Path $ClaudeFile)) {
    Write-Utf8NoBom $ClaudeFile "$ImportLine`n"
    Write-Host "Created $ClaudeFile importing ~/.codex/AGENTS.md."
}
elseif ((Get-Content -Raw $ClaudeFile).Contains($ImportLine)) {
    Write-Host "Already configured: $ClaudeFile imports ~/.codex/AGENTS.md."
}
else {
    Write-Warning "Conflict: $ClaudeFile exists without '$ImportLine'."
    Write-Warning "Keep your existing rules and add this line to $ClaudeFile manually: $ImportLine"
    exit 1
}

Write-Host "Global agent setup complete."
