#requires -Version 5.1
# Regression test for bootstrap-new-project.ps1. Creates throwaway projects for
# every profile, asserts invariants, and cleans up. No dependencies beyond
# PowerShell and git. Run before committing changes to the bootstrap path.

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Bootstrap = Join-Path $ScriptDir "bootstrap-new-project.ps1"
$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("bstest-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force $Tmp | Out-Null

$script:Pass = 0
$script:Fail = 0
function Pass { $script:Pass++ }
function Fail { param([string]$Message) $script:Fail++; Write-Host "  FAIL: $Message" }

function Assert-File { param($Dir, $Rel, $Tag) if (Test-Path (Join-Path $Dir $Rel)) { Pass } else { Fail "${Tag}: missing $Rel" } }
function Assert-Absent { param($Dir, $Rel, $Tag) if (Test-Path (Join-Path $Dir $Rel)) { Fail "${Tag}: unexpected $Rel" } else { Pass } }
function Assert-Grep {
    param($File, $Text, $Tag)
    if ((Test-Path $File) -and ((Get-Content -Raw $File).Contains($Text))) { Pass }
    else { Fail "${Tag}: '$Text' not found in $File" }
}
function Assert-NoBom {
    param($File, $Tag)
    $bytes = [System.IO.File]::ReadAllBytes($File)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Fail "${Tag}: UTF-8 BOM present in $File"
    }
    else { Pass }
}
function Assert-CleanTree {
    param($Dir, $Tag)
    $status = & git -C $Dir status --porcelain
    if ([string]::IsNullOrWhiteSpace($status)) { Pass } else { Fail "${Tag}: git working tree not clean" }
}

function Invoke-Bootstrap {
    param($Dir, $Name, $Profile)
    try { & $Bootstrap -Destination $Dir -ProjectName $Name -Profile $Profile *> $null; return $true }
    catch { return $false }
}

try {
    Write-Host "Core invariants across profiles..."
    foreach ($p in @("minimal", "software", "operated", "all")) {
        $dir = Join-Path $Tmp $p
        if (-not (Invoke-Bootstrap $dir "Test $p" $p)) { Fail "${p}: bootstrap threw"; continue }
        foreach ($f in @("README.md", "AGENTS.md", "CLAUDE.md", "INDEX.md", "PROJECT.md",
                ".editorconfig", ".gitignore", ".gitattributes", ".obsidian/app.json")) {
            Assert-File $dir $f $p
        }
        if ((Get-Content -Raw (Join-Path $dir "CLAUDE.md")).Trim() -eq "@AGENTS.md") { Pass }
        else { Fail "${p}: CLAUDE.md is not exactly '@AGENTS.md'" }
        # Collect MatchInfo objects rather than using -Quiet: over a pipeline of
        # several files -Quiet emits one boolean per file, and a multi-element
        # array is always truthy, which would falsely report a placeholder.
        $placeholders = Get-ChildItem -Recurse -Filter *.md $dir |
            Select-String -Pattern '<PROJECT_NAME>|<YYYY-MM-DD>'
        if ($placeholders) { Fail "${p}: leftover template placeholder" } else { Pass }
        Assert-NoBom (Join-Path $dir "AGENTS.md") $p
        Assert-Grep (Join-Path $dir "AGENTS.md") "Test $p" $p
        Assert-Grep (Join-Path $dir ".gitignore") "CLAUDE.local.md" $p
        Assert-CleanTree $dir $p
    }

    Write-Host "Profile-specific outputs..."
    Assert-Absent $Tmp "minimal/CHANGELOG.md" "minimal"
    Assert-Absent $Tmp "minimal/docs/architecture/ARCHITECTURE.md" "minimal"

    Assert-File $Tmp "software/CHANGELOG.md" "software"
    Assert-File $Tmp "software/docs/architecture/ARCHITECTURE.md" "software"
    Assert-File $Tmp "software/docs/quality/TESTING.md" "software"
    Assert-Absent $Tmp "software/ACTIONS.md" "software"

    Assert-File $Tmp "operated/ACTIONS.md" "operated"
    Assert-File $Tmp "operated/TOOLS.md" "operated"
    Assert-File $Tmp "operated/docs/operations/ENVIRONMENTS.md" "operated"
    Assert-Absent $Tmp "operated/SECURITY.md" "operated"

    Assert-File $Tmp "all/docs/api/INTERFACES.md" "all"
    Assert-File $Tmp "all/docs/data/DATA_MODEL.md" "all"
    Assert-File $Tmp "all/SECURITY.md" "all"
    Assert-File $Tmp "all/docs/security/THREAT_MODEL.md" "all"
    Assert-Absent $Tmp "all/docs/architecture/decisions" "all (no auto ADR dir)"

    Write-Host "Guards..."
    if (Invoke-Bootstrap (Join-Path $Tmp "software") "Dup" "minimal") {
        Fail "guard: bootstrap into a non-empty destination should fail"
    }
    else { Pass }
    if (Invoke-Bootstrap (Join-Path $Tmp "badprofile") "Bad" "nonsense") {
        Fail "guard: invalid profile should fail"
    }
    else { Pass }

    Write-Host ""
    $total = $script:Pass + $script:Fail
    if ($script:Fail -eq 0) {
        Write-Host "All $total checks passed."
    }
    else {
        Write-Host "$($script:Fail) of $total checks FAILED."
        exit 1
    }
}
finally {
    Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue
}
