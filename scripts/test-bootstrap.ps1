#requires -Version 5.1
# Regression tests for bootstrap-new-project.ps1. All Git state is isolated
# from the user's home directory and removed when the test finishes.

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
function Get-GitTreeState {
    param($Dir)
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $status = & git -C $Dir status --porcelain 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    [pscustomobject]@{ ExitCode = $exitCode; Status = ($status -join "`n") }
}
function Invoke-GitProbe {
    param([string]$GitPath, [string[]]$Arguments)
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& $GitPath @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    [pscustomobject]@{ ExitCode = $exitCode; Output = (($output | ForEach-Object { $_.ToString() }) -join "`n") }
}
function Assert-CleanTree {
    param($Dir, $Tag)
    $result = Get-GitTreeState $Dir
    if ($result.ExitCode -ne 0) { Fail "${Tag}: git status failed with code $($result.ExitCode)" }
    elseif ([string]::IsNullOrWhiteSpace($result.Status)) { Pass }
    else { Fail "${Tag}: git working tree not clean" }
}
function Invoke-Bootstrap {
    param($Dir, $Name, $Profile)
    try {
        $output = @(& $Bootstrap -Destination $Dir -ProjectName $Name -Profile $Profile *>&1)
        [pscustomobject]@{ Success = $true; Output = (($output | ForEach-Object { $_.ToString() }) -join "`n") }
    }
    catch {
        [pscustomobject]@{ Success = $false; Output = $_.Exception.Message }
    }
}
function Set-TestIdentity {
    $env:GIT_AUTHOR_NAME = "Bootstrap Test"
    $env:GIT_AUTHOR_EMAIL = "bootstrap@example.invalid"
    $env:GIT_COMMITTER_NAME = "Bootstrap Test"
    $env:GIT_COMMITTER_EMAIL = "bootstrap@example.invalid"
}
function Clear-TestIdentity {
    Remove-Item Env:GIT_AUTHOR_NAME, Env:GIT_AUTHOR_EMAIL, Env:GIT_COMMITTER_NAME, Env:GIT_COMMITTER_EMAIL -ErrorAction SilentlyContinue
}
function New-GitWrapper {
    param([string]$Directory)
    New-Item -ItemType Directory -Force $Directory | Out-Null
    $runningOnWindows = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
    if ($runningOnWindows) {
        $path = Join-Path $Directory "git.cmd"
        $content = @"
@echo off
for %%A in (%*) do if "%%~A"=="%MOCK_GIT_FAIL_COMMAND%" (
  echo mocked git %MOCK_GIT_FAIL_COMMAND% failure 1>&2
  exit /b 42
)
"%REAL_GIT_PATH%" %*
exit /b %ERRORLEVEL%
"@
        [System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.ASCIIEncoding))
    }
    else {
        $path = Join-Path $Directory "git"
        $content = @"
#!/bin/sh
for arg in "`$@"; do
    if [ "`$arg" = "`$MOCK_GIT_FAIL_COMMAND" ]; then
        echo "mocked git `$MOCK_GIT_FAIL_COMMAND failure" >&2
        exit 42
    fi
done
exec "`$REAL_GIT_PATH" "`$@"
"@
        [System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false)))
        & chmod +x $path
        if ($LASTEXITCODE -ne 0) { throw "Could not make mock git executable." }
    }
    $path
}

$savedEnvironment = @{}
foreach ($name in @("PATH", "HOME", "USERPROFILE", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM",
        "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "MOCK_GIT_FAIL_COMMAND",
        "REAL_GIT_PATH", "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0")) {
    $savedEnvironment[$name] = [System.Environment]::GetEnvironmentVariable($name)
}

try {
    $realGitCommand = Get-Command git -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $realGit = $realGitCommand.Source
    $env:REAL_GIT_PATH = $realGit
    $isolatedHome = Join-Path $Tmp "home"
    New-Item -ItemType Directory -Force $isolatedHome | Out-Null
    $env:HOME = $isolatedHome
    $env:USERPROFILE = $isolatedHome
    $env:XDG_CONFIG_HOME = Join-Path $isolatedHome ".config"
    $env:GIT_CONFIG_GLOBAL = Join-Path $isolatedHome "nonexistent.gitconfig"
    $env:GIT_CONFIG_NOSYSTEM = "1"
    $env:GIT_CONFIG_COUNT = "1"
    $env:GIT_CONFIG_KEY_0 = "user.useConfigOnly"
    $env:GIT_CONFIG_VALUE_0 = "true"

    Write-Host "Core invariants across profiles..."
    Set-TestIdentity
    foreach ($p in @("minimal", "software", "operated", "all")) {
        $dir = Join-Path $Tmp $p
        $result = Invoke-Bootstrap $dir "Test $p" $p
        if (-not $result.Success) { Fail "${p}: bootstrap failed: $($result.Output)"; continue }
        foreach ($f in @("README.md", "AGENTS.md", "CLAUDE.md", "INDEX.md", "PROJECT.md",
                ".editorconfig", ".gitignore", ".gitattributes", ".obsidian/app.json")) {
            Assert-File $dir $f $p
        }
        if ((Get-Content -Raw (Join-Path $dir "CLAUDE.md")).Trim() -eq "@AGENTS.md") { Pass }
        else { Fail "${p}: CLAUDE.md is not exactly '@AGENTS.md'" }
        $placeholders = Get-ChildItem -Recurse -Filter *.md $dir | Select-String -Pattern '<PROJECT_NAME>|<YYYY-MM-DD>'
        if ($placeholders) { Fail "${p}: leftover template placeholder" } else { Pass }
        Assert-NoBom (Join-Path $dir "AGENTS.md") $p
        Assert-Grep (Join-Path $dir "AGENTS.md") "Test $p" $p
        Assert-Grep (Join-Path $dir "AGENTS.md") "Always answer the user in Russian" $p
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

    Write-Host "Git identity and failure handling..."
    Clear-TestIdentity
    $noIdentityDir = Join-Path $Tmp "no-identity"
    $result = Invoke-Bootstrap $noIdentityDir "No Identity" "minimal"
    if ($result.Success) { Pass } else { Fail "no identity: bootstrap failed: $($result.Output)" }
    if ($result.Output.Contains("Git identity is not configured")) { Pass } else { Fail "no identity: guidance missing" }
    $probe = Invoke-GitProbe $realGit @("-C", $noIdentityDir, "rev-parse", "--verify", "HEAD")
    if ($probe.ExitCode -ne 0) { Pass } else { Fail "no identity: initial commit unexpectedly exists" }
    $probe = Invoke-GitProbe $realGit @("-C", $noIdentityDir, "diff", "--cached", "--quiet")
    if ($probe.ExitCode -eq 1) { Pass } else { Fail "no identity: generated files are not staged" }

    Set-TestIdentity
    $wrapperDir = Join-Path $Tmp "mock-bin"
    New-GitWrapper $wrapperDir | Out-Null
    $env:PATH = $wrapperDir + [System.IO.Path]::PathSeparator + $savedEnvironment["PATH"]
    foreach ($failedCommand in @("init", "symbolic-ref", "add", "commit")) {
        $env:MOCK_GIT_FAIL_COMMAND = $failedCommand
        $failureDir = Join-Path $Tmp ("fail-" + $failedCommand)
        $result = Invoke-Bootstrap $failureDir "Fail $failedCommand" "minimal"
        if (-not $result.Success) { Pass } else { Fail "mock ${failedCommand}: bootstrap unexpectedly succeeded" }
        if ($result.Output.Contains("git $failedCommand") -and $result.Output.Contains("mocked git $failedCommand failure")) { Pass }
        else { Fail "mock ${failedCommand}: precise Git diagnostic missing: $($result.Output)" }
        if (-not $result.Output.Contains("Initialized git repository with an initial commit")) { Pass }
        else { Fail "mock ${failedCommand}: false success message emitted" }
    }
    Remove-Item Env:MOCK_GIT_FAIL_COMMAND -ErrorAction SilentlyContinue

    Write-Host "git status failure detection..."
    $env:MOCK_GIT_FAIL_COMMAND = "status"
    $treeState = Get-GitTreeState (Join-Path $Tmp "minimal")
    if ($treeState.ExitCode -eq 42) { Pass } else { Fail "git status failure was not detected" }
    Remove-Item Env:MOCK_GIT_FAIL_COMMAND -ErrorAction SilentlyContinue

    Write-Host "Missing Git and guards..."
    $env:PATH = Join-Path $Tmp "empty-path"
    New-Item -ItemType Directory -Force $env:PATH | Out-Null
    $missingGitDir = Join-Path $Tmp "missing-git"
    $result = Invoke-Bootstrap $missingGitDir "Missing Git" "minimal"
    if ($result.Success -and $result.Output.Contains("Git was not found")) { Pass } else { Fail "missing git: explicit success message missing" }
    Assert-Absent $missingGitDir ".git" "missing git"

    $env:PATH = $savedEnvironment["PATH"]
    if ((Invoke-Bootstrap (Join-Path $Tmp "software") "Dup" "minimal").Success) { Fail "guard: non-empty destination accepted" } else { Pass }
    if ((Invoke-Bootstrap (Join-Path $Tmp "badprofile") "Bad" "nonsense").Success) { Fail "guard: invalid profile accepted" } else { Pass }

    Write-Host ""
    $total = $script:Pass + $script:Fail
    if ($script:Fail -eq 0) { Write-Host "All $total checks passed." }
    else { Write-Host "$($script:Fail) of $total checks FAILED."; exit 1 }
}
finally {
    foreach ($name in $savedEnvironment.Keys) {
        [System.Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name])
    }
    Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue
}

exit 0
