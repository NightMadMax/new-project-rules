#requires -Version 5.1
# Smoke tests for global and directory-scoped agent instruction setup.

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$SetupGlobal = Join-Path $ScriptDir "setup-global-agents.ps1"
$AddScope = Join-Path $ScriptDir "add-agent-scope.ps1"
$CheckEnvironment = Join-Path $ScriptDir "check-environment.ps1"
$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("agenttest-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force $Tmp | Out-Null

$script:Pass = 0
$script:Fail = 0
function Pass { $script:Pass++ }
function Fail { param([string]$Message) $script:Fail++; Write-Host "  FAIL: $Message" }
function Invoke-ScriptChecked {
    param([scriptblock]$Action)
    try {
        $output = @(& $Action *>&1)
        [pscustomobject]@{ Success = $true; Output = (($output | ForEach-Object { $_.ToString() }) -join "`n") }
    }
    catch {
        [pscustomobject]@{ Success = $false; Output = $_.Exception.Message }
    }
}
function Assert-ExactContent {
    param([string]$Path, [string]$Expected, [string]$Tag)
    if ((Test-Path -LiteralPath $Path) -and ((Get-Content -Raw -LiteralPath $Path) -replace "(\r?\n)+$", "") -ceq $Expected) { Pass }
    else { Fail "${Tag}: unexpected content in $Path" }
}
function Count-Literal {
    param([string]$Text, [string]$Needle)
    ([regex]::Matches($Text, [regex]::Escape($Needle))).Count
}

try {
    if ($null -eq (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git is required for scoped-agent smoke tests."
    }

    Write-Host "Global setup creation and idempotence..."
    $testHome = Join-Path $Tmp "home"
    $result = Invoke-ScriptChecked { & $SetupGlobal -HomeDirectory $testHome }
    if ($result.Success) { Pass } else { Fail "global create failed: $($result.Output)" }
    $codexFile = Join-Path $testHome ".codex/AGENTS.md"
    $claudeFile = Join-Path $testHome ".claude/CLAUDE.md"
    if (Test-Path -LiteralPath $codexFile) { Pass } else { Fail "global create: AGENTS.md missing" }
    Assert-ExactContent $claudeFile "@~/.codex/AGENTS.md" "global create"

    $custom = "# Preserved global rules`n"
    [System.IO.File]::WriteAllText($codexFile, $custom, (New-Object System.Text.UTF8Encoding($false)))
    $result = Invoke-ScriptChecked { & $SetupGlobal -HomeDirectory $testHome }
    if ($result.Success) { Pass } else { Fail "global rerun failed: $($result.Output)" }
    Assert-ExactContent $codexFile "# Preserved global rules" "global idempotence"
    Assert-ExactContent $claudeFile "@~/.codex/AGENTS.md" "global idempotence"

    Write-Host "Global setup conflict..."
    $conflictHome = Join-Path $Tmp "conflict-home"
    $conflictClaudeDir = Join-Path $conflictHome ".claude"
    New-Item -ItemType Directory -Force $conflictClaudeDir | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $conflictClaudeDir "CLAUDE.md"), "custom rules`n", (New-Object System.Text.UTF8Encoding($false)))
    $result = Invoke-ScriptChecked { & $SetupGlobal -HomeDirectory $conflictHome }
    if (-not $result.Success -and $result.Output.Contains("not the exact one-line import")) { Pass }
    else { Fail "global conflict was not rejected" }
    if (-not (Test-Path -LiteralPath (Join-Path $conflictHome ".codex/AGENTS.md"))) { Pass }
    else { Fail "global conflict changed Codex state before validation" }

    Write-Host "Scoped setup creation, index links, and idempotence..."
    $project = Join-Path $Tmp "project"
    New-Item -ItemType Directory -Force $project | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $project "INDEX.md"), "# Index`n", (New-Object System.Text.UTF8Encoding($false)))
    & git -C $project init *> $null
    if ($LASTEXITCODE -ne 0) { throw "Could not initialize temporary git repository." }
    $scope = Join-Path $project "src/component"
    $result = Invoke-ScriptChecked { & $AddScope -Directory $scope -Rule "Use component conventions." }
    if ($result.Success) { Pass } else { Fail "scope create failed: $($result.Output)" }
    $scopeAgents = Join-Path $scope "AGENTS.md"
    $scopeClaude = Join-Path $scope "CLAUDE.md"
    if ((Test-Path $scopeAgents) -and (Get-Content -Raw $scopeAgents).Contains("Use component conventions.")) { Pass }
    else { Fail "scope create: AGENTS.md missing rule" }
    Assert-ExactContent $scopeClaude "@AGENTS.md" "scope create"
    $index = Get-Content -Raw (Join-Path $project "INDEX.md")
    $agentsLink = "[[src/component/AGENTS|src/component/AGENTS.md]]"
    $claudeLink = "[[src/component/CLAUDE|src/component/CLAUDE.md]]"
    if ((Count-Literal $index $agentsLink) -eq 1 -and (Count-Literal $index $claudeLink) -eq 1) { Pass }
    else { Fail "scope create: INDEX.md links missing or duplicated" }

    $beforeAgents = Get-Content -Raw $scopeAgents
    $result = Invoke-ScriptChecked { & $AddScope -Directory $scope -Rule "Replacement rule." }
    if ($result.Success) { Pass } else { Fail "scope rerun failed: $($result.Output)" }
    if ((Get-Content -Raw $scopeAgents) -ceq $beforeAgents) { Pass } else { Fail "scope rerun overwrote AGENTS.md" }
    $index = Get-Content -Raw (Join-Path $project "INDEX.md")
    if ((Count-Literal $index $agentsLink) -eq 1 -and (Count-Literal $index $claudeLink) -eq 1) { Pass }
    else { Fail "scope rerun duplicated INDEX.md links" }

    Write-Host "Scoped setup conflict..."
    $conflictScope = Join-Path $project "src/conflict"
    New-Item -ItemType Directory -Force $conflictScope | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $conflictScope "CLAUDE.md"), "custom rules`n", (New-Object System.Text.UTF8Encoding($false)))
    $indexBefore = Get-Content -Raw (Join-Path $project "INDEX.md")
    $result = Invoke-ScriptChecked { & $AddScope -Directory $conflictScope -Rule "Should not be written." }
    if (-not $result.Success -and $result.Output.Contains("not the exact one-line import")) { Pass }
    else { Fail "scope conflict was not rejected" }
    if (-not (Test-Path (Join-Path $conflictScope "AGENTS.md"))) { Pass } else { Fail "scope conflict created AGENTS.md" }
    if ((Get-Content -Raw (Join-Path $project "INDEX.md")) -ceq $indexBefore) { Pass } else { Fail "scope conflict changed INDEX.md" }

    Write-Host "Environment check without Git..."
    $emptyPath = Join-Path $Tmp "empty-path"
    New-Item -ItemType Directory -Force $emptyPath | Out-Null
    $engineName = if ($PSVersionTable.PSEdition -eq "Desktop") { "powershell.exe" } else { "pwsh" }
    $engine = Join-Path $PSHOME $engineName
    $savedPath = $env:PATH
    try {
        $env:PATH = $emptyPath
        $environmentOutput = @(& $engine -NoProfile -File $CheckEnvironment 2>&1)
        $environmentExitCode = $LASTEXITCODE
    }
    finally {
        $env:PATH = $savedPath
    }
    $environmentText = ($environmentOutput | ForEach-Object { $_.ToString() }) -join "`n"
    if ($environmentExitCode -eq 1) { Pass } else { Fail "environment check returned $environmentExitCode instead of 1" }
    if ((Count-Literal $environmentText "[MISS] git") -eq 1) { Pass } else { Fail "environment check did not report missing Git exactly once" }
    if ($environmentText.Contains("credential helper not checked because git is unavailable")) { Pass }
    else { Fail "environment check did not skip the Git credential helper safely" }

    Write-Host ""
    $total = $script:Pass + $script:Fail
    if ($script:Fail -eq 0) { Write-Host "All $total checks passed." }
    else { Write-Host "$($script:Fail) of $total checks FAILED."; exit 1 }
}
finally {
    Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue
}
