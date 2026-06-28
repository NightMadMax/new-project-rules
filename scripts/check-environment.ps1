#requires -Version 5.1
# Read-only check of the must-have baseline for the dual Codex + Claude Code
# workflow on Windows. Changes nothing; exits non-zero if a required tool or
# credential is missing. See docs/research/MUST_HAVE_PROJECT_TOOLING_2026.md.

$ErrorActionPreference = "Stop"
$script:Missing = 0

function Test-Has {
    param([string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-Required {
    param([string]$Name, [string]$Note)
    if (Test-Has $Name) { Write-Host "  [ ok ] $Name" }
    else { Write-Host "  [MISS] $Name - $Note"; $script:Missing++ }
}

function Test-Recommended {
    param([string]$Name, [string]$Note)
    if (Test-Has $Name) { Write-Host "  [ ok ] $Name" }
    else { Write-Host "  [ -- ] $Name - $Note" }
}

Write-Host "Required on this machine:"
Test-Required "git" "version control"
Test-Required "gh" "GitHub CLI for repos, pull requests, releases"
Test-Required "codex" "OpenAI Codex agent"
Test-Required "claude" "Anthropic Claude Code agent"

Write-Host ""
Write-Host "Authentication and credentials:"
if (Test-Has "gh") {
    & gh auth status *> $null
    if ($LASTEXITCODE -eq 0) { Write-Host "  [ ok ] gh is authenticated" }
    else { Write-Host "  [MISS] gh is not authenticated - run: gh auth login"; $script:Missing++ }
}
$helper = (& git config --get credential.helper 2>$null)
if ([string]::IsNullOrWhiteSpace($helper)) {
    Write-Host "  [MISS] no git credential helper - configure Git Credential Manager"
    $script:Missing++
}
elseif ($helper -eq "store") {
    Write-Host "  [WARN] credential.helper=store saves tokens UNENCRYPTED; prefer Git Credential Manager"
}
else {
    Write-Host "  [ ok ] credential.helper=$helper"
}
$claudeFile = Join-Path $HOME ".claude/CLAUDE.md"
if (Test-Path $claudeFile) { Write-Host "  [ ok ] ~/.claude/CLAUDE.md present" }
else { Write-Host "  [ -- ] ~/.claude/CLAUDE.md missing - run scripts/setup-global-agents.ps1" }

Write-Host ""
Write-Host "Recommended (not required):"
Test-Recommended "python" "cross-platform automation"
Test-Recommended "pwsh" "PowerShell 7 for testing .ps1 scripts"
Test-Recommended "rg" "ripgrep fast search (often bundled with Claude Code)"
Test-Recommended "winget" "Windows package manager"

Write-Host ""
if ($script:Missing -eq 0) {
    Write-Host "All required tools and credentials are present."
}
else {
    Write-Host "$($script:Missing) required item(s) missing - see [MISS] above."
    exit 1
}
