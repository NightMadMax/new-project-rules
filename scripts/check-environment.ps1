#requires -Version 5.1
# Read-only check of the must-have baseline for the dual Codex + Claude Code
# workflow on Windows. Changes nothing; exits non-zero if a required tool or
# credential is missing. See docs/research/MUST_HAVE_PROJECT_TOOLING_2026.md.

param(
    [ValidateSet("codex", "claude", "both")]
    [string]$AgentMode = "both"
)

$ErrorActionPreference = "Stop"
$script:Missing = 0

function Get-Launchable {
    # A name on PATH is not a tool. An App Execution Alias is a zero-byte file
    # that resolves like an executable and then refuses to run, and the working
    # binary is often further along the same PATH - so every hit is tried, the
    # zero-length ones without being started (starting one opens the Store).
    # Canonical implementation and the known install locations outside PATH:
    # scripts/cli_discovery.py, which needs Python this script cannot assume.
    param([string]$Name)
    foreach ($Command in @(Get-Command $Name -All -ErrorAction SilentlyContinue)) {
        if ($Command.CommandType -ne "Application") { continue }
        $Item = Get-Item $Command.Source -ErrorAction SilentlyContinue
        if ($null -eq $Item -or $Item.Length -eq 0) { continue }
        & $Command.Source --version *> $null
        if ($LASTEXITCODE -eq 0) { return $Command.Source }
    }
    $null
}

function Test-Has {
    param([string]$Name)
    $null -ne (Get-Launchable $Name)
}

function Test-Required {
    param([string]$Name, [string]$Note)
    if (Test-Has $Name) { Write-Host "  [ ok ] $Name" }
    else { Write-Host "  [MISS] $Name - $Note (не найден запускаемый бинарник)"; $script:Missing++ }
}

function Test-Recommended {
    param([string]$Name, [string]$Note)
    if (Test-Has $Name) { Write-Host "  [ ok ] $Name" }
    else { Write-Host "  [ -- ] $Name - $Note" }
}

Write-Host "Required on this machine (agent mode: $AgentMode):"
Test-Required "git" "version control"
Test-Required "gh" "GitHub CLI for repos, pull requests, releases"
if ($AgentMode -in @("codex", "both")) {
    Test-Required "codex" "OpenAI Codex agent; вне PATH его найдёт scripts/check-cli.ps1"
}
if ($AgentMode -in @("claude", "both")) {
    Test-Required "claude" "Anthropic Claude Code agent; вне PATH его найдёт scripts/check-cli.ps1"
}
$hasGit = Test-Has "git"

Write-Host ""
Write-Host "Authentication and credentials:"
if (Test-Has "gh") {
    & gh auth status *> $null
    if ($LASTEXITCODE -eq 0) { Write-Host "  [ ok ] gh is authenticated" }
    else { Write-Host "  [MISS] gh is not authenticated - run: gh auth login"; $script:Missing++ }
}
if ($hasGit) {
    $transport = ""
    if (Test-Has "gh") {
        $transport = (& gh config get git_protocol 2>$null)
    }
    $helper = (& git config --get credential.helper 2>$null)
    if ($transport -eq "ssh" -and [string]::IsNullOrWhiteSpace($helper)) {
        # SSH transport authenticates with keys; a credential helper is not used.
        Write-Host "  [ ok ] git transport is SSH (gh git_protocol=ssh); credential helper not required"
    }
    elseif ([string]::IsNullOrWhiteSpace($helper)) {
        Write-Host "  [MISS] no git credential helper - configure Git Credential Manager"
        $script:Missing++
    }
    elseif ($helper -eq "store") {
        Write-Host "  [WARN] credential.helper=store saves tokens UNENCRYPTED; prefer Git Credential Manager"
    }
    else {
        Write-Host "  [ ok ] credential.helper=$helper"
    }
}
else {
    Write-Host "  [ -- ] git credential helper not checked because git is unavailable"
}
if ($AgentMode -in @("claude", "both")) {
    $claudeFile = Join-Path $HOME ".claude/CLAUDE.md"
    if (Test-Path $claudeFile) { Write-Host "  [ ok ] ~/.claude/CLAUDE.md present" }
    else { Write-Host "  [ -- ] ~/.claude/CLAUDE.md missing - run scripts/setup-global-agents.ps1" }
}

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
