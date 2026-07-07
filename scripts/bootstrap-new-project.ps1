param(
    [Parameter(Mandatory = $true)]
    [string]$Destination,

    [Parameter(Mandatory = $true)]
    [string]$ProjectName,

    [ValidateSet("minimal", "software", "operated", "all")]
    [string]$Profile = "minimal"
)

$ErrorActionPreference = "Stop"
$RulesRoot = Split-Path -Parent $PSScriptRoot
$Templates = Join-Path $RulesRoot "templates/new-project"
$Manifest = Join-Path $RulesRoot "config/profiles.tsv"
$StandardSourceFile = Join-Path $RulesRoot "config/standard-source.txt"
$StandardVersionFile = Join-Path $RulesRoot "STANDARD_VERSION"
$MigrationsManifest = Join-Path $RulesRoot "config/migrations.tsv"
$ProfileRanks = @{ minimal = 0; software = 1; operated = 2; all = 3 }
$git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $git) {
    throw "Git is required to record project-standard provenance and initialize the project repository."
}
$StandardSource = (Get-Content -Raw -Encoding utf8 $StandardSourceFile).Trim()
$StandardVersion = (Get-Content -Raw -Encoding utf8 $StandardVersionFile).Trim()
if ($StandardSource -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { throw "Invalid standard source: $StandardSource" }
if ($StandardVersion -notmatch '^[1-9][0-9]*$') { throw "Invalid STANDARD_VERSION: $StandardVersion" }
$MigrationRows = @(Get-Content -Encoding utf8 $MigrationsManifest | ConvertFrom-Csv -Delimiter "`t")
$ProjectMigrationIds = @()
$MigrationSchema = 0
while ($MigrationSchema -lt [int]$StandardVersion) {
    $Next = @($MigrationRows | Where-Object {
            $_.target -eq "project" -and [int]$_.from_schema -eq $MigrationSchema
        })
    if ($Next.Count -ne 1) { throw "Invalid project migration path from schema $MigrationSchema" }
    $ToSchema = [int]$Next[0].to_schema
    if ($ToSchema -le $MigrationSchema -or $ToSchema -gt [int]$StandardVersion) {
        throw "Invalid project migration transition $MigrationSchema->$ToSchema"
    }
    $ProjectMigrationIds += $Next[0].migration_id
    $MigrationSchema = $ToSchema
}
$sourceCommitOutput = @(& $git.Source -C $RulesRoot rev-parse --verify HEAD 2>$null)
$sourceCommitExitCode = $LASTEXITCODE
$SourceCommit = if ($sourceCommitOutput.Count -gt 0) { $sourceCommitOutput[0].ToString().Trim() } else { "" }
if ($sourceCommitExitCode -ne 0 -or $SourceCommit -notmatch '^[0-9a-f]{40}$') {
    throw "Cannot resolve a valid new-project-rules source commit from $RulesRoot."
}
$ExpectedManifestHeader = "minimum_profile`tsource`tdestination`troot_purpose`tdocs_section`tdocs_label"
$ManifestLines = @(Get-Content -Encoding utf8 $Manifest)
if ($ManifestLines.Count -lt 2 -or $ManifestLines[0] -cne $ExpectedManifestHeader) {
    throw "Invalid project profile manifest header: $Manifest"
}
$Artifacts = @($ManifestLines | ConvertFrom-Csv -Delimiter "`t")
$SeenDestinations = @{}
$GeneratedDestinations = @(".editorconfig", ".gitattributes", ".gitignore", ".project-standard.json", "CLAUDE.md")
foreach ($artifact in $Artifacts) {
    if (-not $ProfileRanks.ContainsKey($artifact.minimum_profile)) {
        throw "Unknown minimum_profile '$($artifact.minimum_profile)' in $Manifest"
    }
    if ([System.IO.Path]::IsPathRooted($artifact.destination) -or
            ($artifact.destination -split '/' | Where-Object { $_ -eq '..' }).Count -gt 0) {
        throw "Unsafe destination '$($artifact.destination)' in $Manifest"
    }
    if ($SeenDestinations.ContainsKey($artifact.destination)) {
        throw "Duplicate destination '$($artifact.destination)' in $Manifest"
    }
    $SeenDestinations[$artifact.destination] = $true
    if ($artifact.source -eq "@generated") {
        if ($artifact.destination -notin $GeneratedDestinations) {
            throw "Unknown generated artifact '$($artifact.destination)' in $Manifest"
        }
    }
    elseif (-not (Test-Path -LiteralPath (Join-Path $Templates $artifact.source) -PathType Leaf)) {
        throw "Template not found for '$($artifact.destination)': $($artifact.source)"
    }
    if (($artifact.docs_section -eq "-") -ne ($artifact.docs_label -eq "-")) {
        throw "docs_section and docs_label must both be '-' or both be set for '$($artifact.destination)'"
    }
}
$SelectedArtifacts = @($Artifacts | Where-Object {
        $ProfileRanks[$_.minimum_profile] -le $ProfileRanks[$Profile]
    })

# Write UTF-8 without a BOM on every PowerShell edition. Windows PowerShell 5.1
# "-Encoding utf8" emits a BOM, which corrupts the LF-normalized Markdown and
# shell files this repository ships, so always go through these helpers.
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-Utf8NoBom {
    param([string]$Path, $Content)
    if ($Content -is [array]) {
        $text = ($Content -join "`n") + "`n"
    }
    else {
        $text = [string]$Content
    }
    [System.IO.File]::WriteAllText($Path, $text, $Utf8NoBom)
}

function Append-Utf8NoBom {
    param([string]$Path, [string]$Line)
    [System.IO.File]::AppendAllText($Path, $Line + "`n", $Utf8NoBom)
}

$DestinationExisted = Test-Path $Destination
if ($DestinationExisted) {
    $existing = Get-ChildItem -Force $Destination | Select-Object -First 1
    if ($null -ne $existing) {
        throw "Destination is not empty: $Destination"
    }
}

$BootstrapSucceeded = $false
try {
New-Item -ItemType Directory -Force $Destination | Out-Null
# Resolve to an absolute path so [System.IO.File] calls do not depend on the
# process current directory, which can differ from the PowerShell location.
$Destination = (Resolve-Path $Destination).Path

$Today = Get-Date -Format "yyyy-MM-dd"

function Install-Template {
    param([string]$Source, [string]$Target)

    $targetPath = Join-Path $Destination $Target
    $targetDirectory = Split-Path -Parent $targetPath
    New-Item -ItemType Directory -Force $targetDirectory | Out-Null
    $content = Get-Content -Raw -Encoding utf8 (Join-Path $Templates $Source)
    $content = $content.Replace("<PROJECT_NAME>", $ProjectName).Replace("<YYYY-MM-DD>", $Today).Replace("<SCHEMA_VERSION>", $StandardVersion)
    Write-Utf8NoBom $targetPath $content
}

function Install-Generated {
    param([string]$Target)
    switch ($Target) {
        ".gitignore" {
            Write-Utf8NoBom (Join-Path $Destination $Target) @(
                ".DS_Store", "Thumbs.db", ".obsidian/", ".trash/", "CLAUDE.local.md",
                ".claude/settings.local.json", ".claude/scheduled_tasks.lock"
            )
        }
        ".gitattributes" {
            Write-Utf8NoBom (Join-Path $Destination $Target) @(
                "* text=auto", "*.sh text eol=lf", "*.ps1 text eol=crlf",
                "*.md text eol=lf", "*.json text eol=lf"
            )
        }
        ".editorconfig" {
            Write-Utf8NoBom (Join-Path $Destination $Target) @(
                "# EditorConfig - https://editorconfig.org", "root = true", "", "[*]",
                "charset = utf-8", "end_of_line = lf", "insert_final_newline = true",
                "trim_trailing_whitespace = true", "indent_style = space", "indent_size = 2",
                "", "[*.md]", "trim_trailing_whitespace = false", "", "[*.ps1]",
                "end_of_line = crlf", "indent_size = 4", "", "[Makefile]",
                "indent_style = tab", "", "[*.go]", "indent_style = tab"
            )
        }
        "CLAUDE.md" { Write-Utf8NoBom (Join-Path $Destination $Target) "@AGENTS.md`n" }
        ".project-standard.json" {
            $metadata = [ordered]@{
                schema_version = [int]$StandardVersion
                profile = $Profile
                source = $StandardSource
                source_commit = $SourceCommit
                created_at = $Today
                adopted_at = $Today
                applied_migrations = @($ProjectMigrationIds)
            }
            Write-Utf8NoBom (Join-Path $Destination $Target) (($metadata | ConvertTo-Json -Depth 3) + "`n")
        }
        default { throw "Unknown generated artifact: $Target" }
    }
}

foreach ($artifact in $SelectedArtifacts) {
    if ($artifact.source -eq "@generated") {
        Install-Generated $artifact.destination
    }
    else {
        Install-Template $artifact.source $artifact.destination
    }
}

function Ensure-IndexEntry {
    param([string]$Path, [string]$Purpose)
    if ($Purpose -eq "-") { return }
    $LinkPath = $Path -replace '\.md$', ''
    $indexPath = Join-Path $Destination "INDEX.md"
    $indexContent = Get-Content -Raw -Encoding utf8 $indexPath
    if (-not $indexContent.Contains("[[$LinkPath")) {
        Append-Utf8NoBom $indexPath "| [[$LinkPath|$Path]] | $Purpose |"
    }
}

function Ensure-DocsIndexEntry {
    param(
        [string]$Heading,
        [string]$Path,
        [string]$Label
    )
    if ($Heading -eq "-") { return }
    $docsIndex = Join-Path $Destination "docs/README.md"
    $linkPath = $Path -replace '\.md$', ''
    $docsContent = Get-Content -Raw -Encoding utf8 $docsIndex
    if (-not $docsContent.Contains("[[$linkPath")) {
        Append-Utf8NoBom $docsIndex ""
        Append-Utf8NoBom $docsIndex "## $Heading"
        Append-Utf8NoBom $docsIndex ""
        Append-Utf8NoBom $docsIndex "- [[$linkPath|$Label]]"
    }
}

foreach ($artifact in $SelectedArtifacts) {
    Ensure-IndexEntry $artifact.destination $artifact.root_purpose
    Ensure-DocsIndexEntry $artifact.docs_section $artifact.destination $artifact.docs_label
}

if ($null -ne $git) {
    function Invoke-GitRequired {
        param(
            [string]$Step,
            [string[]]$Arguments
        )

        $previousErrorActionPreference = $ErrorActionPreference
        try {
            # Windows PowerShell 5.1 converts native stderr into ErrorRecord
            # objects. Decide success from LASTEXITCODE and retain stderr text.
            $ErrorActionPreference = "Continue"
            $output = @(& $git.Source -C $Destination @Arguments 2>&1)
            $exitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        if ($exitCode -ne 0) {
            $details = ($output | ForEach-Object { $_.ToString() }) -join "`n"
            if ([string]::IsNullOrWhiteSpace($details)) {
                $details = "git exited with code $exitCode"
            }
            throw "$Step failed:`n$details"
        }
    }

    Invoke-GitRequired "git init" @("init", "-q")
    Invoke-GitRequired "git symbolic-ref" @("symbolic-ref", "HEAD", "refs/heads/main")
    Invoke-GitRequired "git add" @("add", "-A")

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $git.Source -C $Destination var GIT_AUTHOR_IDENT 2>$null | Out-Null
        $hasAuthorIdentity = $LASTEXITCODE -eq 0
        & $git.Source -C $Destination var GIT_COMMITTER_IDENT 2>$null | Out-Null
        $hasCommitterIdentity = $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if (-not ($hasAuthorIdentity -and $hasCommitterIdentity)) {
        Write-Host "Initialized git repository and staged the initial state."
        Write-Host "Git identity is not configured; set user.name and user.email, then run: git commit -m 'Bootstrap project with new-project-rules'"
    }
    else {
        Invoke-GitRequired "git commit" @("commit", "-m", "Bootstrap project with new-project-rules")
        Write-Host "Initialized git repository with an initial commit."
    }
}
Write-Host "Created '$ProjectName' at $Destination using profile '$Profile'."
Write-Host "Keep this project inside the parent Obsidian vault, review INDEX.md, then create its GitHub repository."
$BootstrapSucceeded = $true
}
finally {
    if (-not $BootstrapSucceeded -and (Test-Path -LiteralPath $Destination)) {
        Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction SilentlyContinue
        if ($DestinationExisted) {
            New-Item -ItemType Directory -Force $Destination | Out-Null
        }
    }
}
exit 0
