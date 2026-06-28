#requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Failures = 0

function Test-Skill {
    param([string]$Name)

    $canonical = Join-Path $Root ".agents/skills/$Name/SKILL.md"
    $bridge = Join-Path $Root ".claude/skills/$Name/SKILL.md"
    $metadata = Join-Path $Root ".agents/skills/$Name/agents/openai.yaml"

    foreach ($file in @($canonical, $bridge, $metadata)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            Write-Host "FAIL: missing $file"
            $script:Failures++
        }
    }
    if ($script:Failures -ne 0) { return }

    $canonicalText = Get-Content -Raw -Encoding UTF8 $canonical
    $bridgeText = Get-Content -Raw -Encoding UTF8 $bridge
    $metadataText = Get-Content -Raw -Encoding UTF8 $metadata
    $canonicalName = [regex]::Match($canonicalText, '(?m)^name: (.+)$').Groups[1].Value.Trim()
    $bridgeName = [regex]::Match($bridgeText, '(?m)^name: (.+)$').Groups[1].Value.Trim()
    $canonicalDescription = [regex]::Match($canonicalText, '(?m)^description: (.+)$').Groups[1].Value.Trim()
    $bridgeDescription = [regex]::Match($bridgeText, '(?m)^description: (.+)$').Groups[1].Value.Trim()

    if ($canonicalName -ne $Name -or $bridgeName -ne $Name) {
        Write-Host "FAIL: name mismatch for $Name"
        $script:Failures++
    }
    if ([string]::IsNullOrWhiteSpace($canonicalDescription) -or
            $canonicalDescription -cne $bridgeDescription) {
        Write-Host "FAIL: description mismatch for $Name"
        $script:Failures++
    }
    if ($canonicalText -match 'TODO|\[TODO' -or $bridgeText -match 'TODO|\[TODO') {
        Write-Host "FAIL: TODO remains in $Name"
        $script:Failures++
    }
    if ($bridgeText -notmatch [regex]::Escape("../../../.agents/skills/$Name/SKILL.md")) {
        Write-Host "FAIL: Claude bridge target mismatch for $Name"
        $script:Failures++
    }
    if ($metadataText -match '[^\x00-\x7F]') {
        Write-Host "FAIL: non-ASCII UI metadata for $Name"
        $script:Failures++
    }
}

Test-Skill "setup-new-computer"
Test-Skill "create-new-project"

if ($Failures -ne 0) {
    Write-Host "$Failures skill check(s) failed."
    exit 1
}

Write-Host "All skill checks passed."
exit 0
