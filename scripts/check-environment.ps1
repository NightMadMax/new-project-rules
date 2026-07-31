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

function Test-Starts {
    # Whether this exact file starts and answers. Every way it can fail is an
    # answer about one candidate, never a reason to stop the check:
    # under $ErrorActionPreference = "Stop" a native command that merely writes
    # to stderr becomes a terminating error, and a file the OS refuses to run
    # throws outright. A stale $LASTEXITCODE would otherwise speak for a call
    # that never happened.
    param([string]$Path)
    $Previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $global:LASTEXITCODE = $null
    try { & $Path --version *> $null }
    catch { return $false }
    finally { $ErrorActionPreference = $Previous }
    return $LASTEXITCODE -eq 0
}

# The canon knows the install locations outside PATH; this script cannot assume
# Python, so it delegates when Python is there and keeps the PATH walk as the
# fallback. Without this the two disagree about the same machine: check-cli finds
# and starts a CLI that check-environment reports as missing.
$script:Discovery = @{}
function Read-Discovery {
    param([string[]]$Names)
    . (Join-Path $PSScriptRoot "lib/Find-Python.ps1")
    $Python = Find-Python39
    if ($null -eq $Python) { return }
    $Script = Join-Path $PSScriptRoot "cli_discovery.py"
    if (-not (Test-Path -LiteralPath $Script)) { return }
    $Previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { $Report = & $Python.Source $Script "--json" @Names 2>$null | Out-String }
    catch { return }
    finally { $ErrorActionPreference = $Previous }
    try { $Parsed = $Report | ConvertFrom-Json } catch { return }
    foreach ($Entry in @($Parsed)) { $script:Discovery[$Entry.tool] = $Entry }
}

function Get-Launchable {
    # A name on PATH is not a tool. An App Execution Alias is a zero-byte file
    # that resolves like an executable and then refuses to run, and the working
    # binary is often further along the same PATH - so every hit is tried, the
    # zero-length ones without being started (starting one opens the Store).
    # Canonical implementation and the known install locations outside PATH:
    # scripts/cli_discovery.py, which needs Python this script cannot assume.
    param([string]$Name)
    if ($script:Discovery.ContainsKey($Name)) {
        $Entry = $script:Discovery[$Name]
        if ($Entry.status -eq "ok") { return $Entry.path }
        return $null
    }
    foreach ($Command in @(Get-Command $Name -All -ErrorAction SilentlyContinue)) {
        if ($Command.CommandType -ne "Application") { continue }
        $Item = Get-Item $Command.Source -ErrorAction SilentlyContinue
        if ($null -eq $Item -or $Item.Length -eq 0) { continue }
        if (Test-Starts $Command.Source) { return $Command.Source }
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
    else { Write-Host "  [MISS] $Name - $Note (no launchable binary found)"; $script:Missing++ }
}

function Test-Recommended {
    param([string]$Name, [string]$Note)
    if (Test-Has $Name) { Write-Host "  [ ok ] $Name" }
    else { Write-Host "  [ -- ] $Name - $Note" }
}

Read-Discovery @("git", "gh", "codex", "claude")

Write-Host "Required on this machine (agent mode: $AgentMode):"
Test-Required "git" "version control"
Test-Required "gh" "GitHub CLI for repos, pull requests, releases"
if ($AgentMode -in @("codex", "both")) {
    Test-Required "codex" "OpenAI Codex agent; outside PATH it is found by scripts/check-cli.ps1"
}
if ($AgentMode -in @("claude", "both")) {
    Test-Required "claude" "Anthropic Claude Code agent; outside PATH it is found by scripts/check-cli.ps1"
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
