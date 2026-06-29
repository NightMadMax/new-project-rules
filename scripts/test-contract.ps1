#requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Bootstrap = Join-Path $PSScriptRoot "bootstrap-new-project.ps1"
$Manifest = Join-Path $Root "config/profiles.tsv"
$PolicyContract = Join-Path $Root "config/policy-contract.tsv"
$Templates = Join-Path $Root "templates/new-project"
$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("contracttest-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
$script:Pass = 0
$script:Fail = 0

function Pass { $script:Pass++ }
function Fail { param([string]$Message) $script:Fail++; Write-Host "  FAIL: $Message" }
function Includes-Profile {
    param($Row, [string]$Profile, $Ranks)
    $Ranks[$Row.minimum_profile] -le $Ranks[$Profile]
}

$savedEnvironment = @{}
$environmentNames = @(
    "HOME", "USERPROFILE", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM",
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"
)
foreach ($name in $environmentNames) {
    $savedEnvironment[$name] = [System.Environment]::GetEnvironmentVariable($name)
}

New-Item -ItemType Directory -Force $Tmp | Out-Null
try {
    Write-Host "Contract structure..."
    $version = (Get-Content -Raw -Encoding UTF8 (Join-Path $Root "STANDARD_VERSION")).Trim()
    if ($version -match '^[1-9][0-9]*$') { Pass } else { Fail "STANDARD_VERSION must be a positive integer" }

    $rows = @(Get-Content -Encoding UTF8 $Manifest | ConvertFrom-Csv -Delimiter "`t")
    $ranks = @{ minimal = 0; software = 1; operated = 2; all = 3 }
    $destinations = @{}
    foreach ($row in $rows) {
        if (-not $ranks.ContainsKey($row.minimum_profile)) {
            Fail "unknown minimum_profile '$($row.minimum_profile)'"
        }
        if ([System.IO.Path]::IsPathRooted($row.destination) -or
                ($row.destination -split '/' | Where-Object { $_ -eq '..' }).Count -gt 0) {
            Fail "unsafe destination '$($row.destination)'"
        }
        if ($destinations.ContainsKey($row.destination)) {
            Fail "duplicate destination '$($row.destination)'"
        }
        else {
            $destinations[$row.destination] = $true
        }
        if ($row.source -ne "@generated" -and
                -not (Test-Path -LiteralPath (Join-Path $Templates $row.source) -PathType Leaf)) {
            Fail "missing template '$($row.source)'"
        }
        if ($row.root_index -notin @("yes", "no") -or $row.docs_index -notin @("yes", "no")) {
            Fail "invalid index relationship for '$($row.destination)'"
        }
    }
    if ($script:Fail -eq 0) { Pass }

    foreach ($policy in @(Get-Content -Encoding UTF8 $PolicyContract | ConvertFrom-Csv -Delimiter "`t")) {
        $path = Join-Path $Root $policy.file
        if ((Test-Path -LiteralPath $path -PathType Leaf) -and
                (Get-Content -Raw -Encoding UTF8 $path).Contains($policy.required_literal)) {
            Pass
        }
        else {
            Fail "policy literal '$($policy.required_literal)' missing from '$($policy.file)'"
        }
    }

    Write-Host "Bootstrap parity across profiles..."
    $env:HOME = Join-Path $Tmp "home"
    $env:USERPROFILE = $env:HOME
    $env:XDG_CONFIG_HOME = Join-Path $env:HOME ".config"
    $env:GIT_CONFIG_GLOBAL = Join-Path $env:HOME "nonexistent.gitconfig"
    $env:GIT_CONFIG_NOSYSTEM = "1"
    $env:GIT_AUTHOR_NAME = "Contract Test"
    $env:GIT_AUTHOR_EMAIL = "contract@example.invalid"
    $env:GIT_COMMITTER_NAME = "Contract Test"
    $env:GIT_COMMITTER_EMAIL = "contract@example.invalid"
    New-Item -ItemType Directory -Force $env:HOME | Out-Null

    foreach ($profile in @("minimal", "software", "operated", "all")) {
        $destination = Join-Path $Tmp $profile
        try {
            & $Bootstrap -Destination $destination -ProjectName "Contract $profile" -Profile $profile *> $null
        }
        catch {
            Fail "${profile}: bootstrap failed: $($_.Exception.Message)"
            continue
        }

        $expected = @($rows | Where-Object { Includes-Profile $_ $profile $ranks } |
                ForEach-Object { $_.destination } | Sort-Object)
        $actual = @(Get-ChildItem -LiteralPath $destination -Recurse -Force -File |
                Where-Object { $_.FullName -notlike (Join-Path $destination ".git\*") } |
                ForEach-Object { $_.FullName.Substring($destination.Length + 1).Replace('\', '/') } |
                Sort-Object)
        $difference = @(Compare-Object -ReferenceObject $expected -DifferenceObject $actual)
        if ($difference.Count -eq 0) { Pass }
        else { Fail "${profile}: generated files differ from config/profiles.tsv: $($difference -join '; ')" }

        $rootIndex = Get-Content -Raw -Encoding UTF8 (Join-Path $destination "INDEX.md")
        $docsIndexPath = Join-Path $destination "docs/README.md"
        $docsIndex = if (Test-Path -LiteralPath $docsIndexPath) { Get-Content -Raw -Encoding UTF8 $docsIndexPath } else { "" }
        foreach ($row in $rows | Where-Object { Includes-Profile $_ $profile $ranks }) {
            $linkPath = $row.destination -replace '\.md$', ''
            if ($row.root_index -eq "yes") {
                if ($rootIndex.Contains("[[$linkPath")) { Pass }
                else { Fail "${profile}: root INDEX.md misses '$linkPath'" }
            }
            if ($row.docs_index -eq "yes") {
                if ($docsIndex.Contains("[[$linkPath")) { Pass }
                else { Fail "${profile}: docs/README.md misses '$linkPath'" }
            }
        }
    }
}
finally {
    foreach ($name in $savedEnvironment.Keys) {
        [System.Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name])
    }
    Remove-Item -LiteralPath $Tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
$total = $script:Pass + $script:Fail
if ($script:Fail -eq 0) {
    Write-Host "All $total contract checks passed."
    exit 0
}
Write-Host "$($script:Fail) of $total contract checks FAILED."
exit 1
