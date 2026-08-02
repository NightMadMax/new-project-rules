#requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Failures = 0

function Test-RequiredLiterals {
    param(
        [string]$File,
        [string[]]$Literals
    )

    $text = Get-Content -Raw -Encoding UTF8 $File
    foreach ($literal in $Literals) {
        if (-not $text.Contains($literal)) {
            Write-Host "FAIL: missing required literal '$literal' in $File"
            $script:Failures++
        }
    }
}

. (Join-Path $PSScriptRoot "lib/Find-Python.ps1")

$Python = Find-Python39
if ($null -eq $Python) {
    Write-Host "FAIL: Python 3.9+ is required for skill checks."
    exit 1
}

# Skill contracts live in config/skills.tsv and are checked by one shared
# implementation, so adding a skill does not mean editing this test.
& $Python.Source (Join-Path $PSScriptRoot "check_skills.py") --root $Root
if ($LASTEXITCODE -ne 0) { $Failures++ }

# The same four literals the shell pair checks. One of them was checked here and
# three were not, so the PowerShell verdict could be green on a file the shell
# verdict rejected -- a parity test that does not test parity.
# The literals come from one file both pairs read. Writing them out in each test
# is what let the two drift apart, and Cyrillic in a .ps1 source does not survive
# Windows PowerShell 5.1, which reads a file without a BOM as ANSI -- the parse
# error this test hit in CI.
$literalsFile = Join-Path $PSScriptRoot "lib/skill-literals.txt"
$requiredLiterals = @(
    Get-Content -Encoding UTF8 $literalsFile |
        Where-Object { $_ -and -not $_.StartsWith("#") }
)
if ($requiredLiterals.Count -eq 0) {
    Write-Host "FAIL: $literalsFile lists no literals"
    $Failures++
}

$reflectSkill = Join-Path $Root ".agents/skills/reflect-and-record/SKILL.md"
Test-RequiredLiterals -File $reflectSkill -Literals $requiredLiterals
# The retired prohibition must stay retired: its return would quietly reinstate
# a rule the project decided against. Built from code points so this source
# stays ASCII-only.
$retired = -join ([char]0x043D, [char]0x0435, [char]0x0020, [char]0x0432,
    [char]0x0020, [char]0x0441, [char]0x0435, [char]0x0440, [char]0x0435,
    [char]0x0434, [char]0x0438, [char]0x043D, [char]0x0435)
if ((Get-Content -Raw -Encoding UTF8 $reflectSkill).Contains($retired)) {
    Write-Host "FAIL: reflect-and-record retains the retired mid-session edit prohibition"
    $Failures++
}

$requiredHeadings = @("## Knowledge Promotion", "## Defect Tracking")
$sharedRuleLiterals = @(
    'docs/quality/DEFECTS.md',
    'immediately upon discovery',
    'section where the entry',
    '`Open`, `Fixed`, or `Won''t Fix`',
    'move the entry to `Fixed`',
    'docs/quality/PLAYBOOK.md',
    'automatically, without waiting for a user reminder',
    'working solution found after testing',
    'raw memory directories.',
    'validator, script, or skill',
    'reusable engineering practice'
)
foreach ($file in @(
    (Join-Path $Root "AGENTS.md"),
    (Join-Path $Root "templates/new-project/AGENTS.template.md")
)) {
    $text = Get-Content -Raw -Encoding UTF8 $file
    foreach ($heading in $requiredHeadings) {
        if ($text -notmatch [regex]::Escape($heading)) {
            Write-Host "FAIL: missing '$heading' in $file"
            $Failures++
        }
    }
    Test-RequiredLiterals -File $file -Literals $sharedRuleLiterals
}

$agentsTemplate = Join-Path $Root "templates/new-project/AGENTS.template.md"
# A hardcoded schema in the managed marker ships a template that claims a
# version it was not rendered for.
if (-not (Get-Content -Raw -Encoding UTF8 $agentsTemplate).Contains('new-project-rules:begin schema=<SCHEMA_VERSION>')) {
    Write-Host "FAIL: AGENTS.template.md managed marker must use the <SCHEMA_VERSION> placeholder, not a hardcoded schema"
    $Failures++
}
foreach ($file in @((Join-Path $Root "AGENTS.md"), $agentsTemplate)) {
    $text = Get-Content -Raw -Encoding UTF8 $file
    $compactCount = ([regex]::Matches($text, [regex]::Escape('project_doc_max_bytes'))).Count
    $processCount = ([regex]::Matches($text, [regex]::Escape('codex --ask-for-approval never'))).Count
    if ($compactCount -ne 1) {
        Write-Host "FAIL: $file must contain exactly one instruction-size rule"
        $Failures++
    }
    if ($processCount -ne 1) {
        Write-Host "FAIL: $file must contain exactly one new-process verification rule"
        $Failures++
    }
}
if ((Get-Content -Raw -Encoding UTF8 $agentsTemplate).Contains('do not create repositories')) {
    Write-Host "FAIL: project baseline must not own new-project repository creation policy"
    $Failures++
}

if ($Failures -ne 0) {
    Write-Host "$Failures skill check(s) failed."
    exit 1
}

Write-Host "All skill checks passed."
exit 0
