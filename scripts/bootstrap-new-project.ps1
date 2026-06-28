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

if (Test-Path $Destination) {
    $existing = Get-ChildItem -Force $Destination | Select-Object -First 1
    if ($null -ne $existing) {
        throw "Destination is not empty: $Destination"
    }
}

New-Item -ItemType Directory -Force (Join-Path $Destination ".obsidian") | Out-Null
# Resolve to an absolute path so [System.IO.File] calls do not depend on the
# process current directory, which can differ from the PowerShell location.
$Destination = (Resolve-Path $Destination).Path

Write-Utf8NoBom (Join-Path $Destination ".obsidian/app.json") "{}`n"
Write-Utf8NoBom (Join-Path $Destination ".gitignore") @(
    ".DS_Store"
    "Thumbs.db"
    ".trash/"
    ".obsidian/workspace.json"
    ".obsidian/workspace-mobile.json"
    ".obsidian/cache/"
    "CLAUDE.local.md"
    ".claude/settings.local.json"
    ".claude/scheduled_tasks.lock"
)
Write-Utf8NoBom (Join-Path $Destination ".gitattributes") @(
    "* text=auto"
    "*.sh text eol=lf"
    "*.ps1 text eol=crlf"
    "*.md text eol=lf"
    "*.json text eol=lf"
)
# EditorConfig is the one language-agnostic, zero-dependency formatting baseline
# every editor honours, so it belongs in the required core of every project.
Write-Utf8NoBom (Join-Path $Destination ".editorconfig") @(
    "# EditorConfig - https://editorconfig.org"
    "root = true"
    ""
    "[*]"
    "charset = utf-8"
    "end_of_line = lf"
    "insert_final_newline = true"
    "trim_trailing_whitespace = true"
    "indent_style = space"
    "indent_size = 2"
    ""
    "[*.md]"
    "trim_trailing_whitespace = false"
    ""
    "[*.ps1]"
    "end_of_line = crlf"
    "indent_size = 4"
    ""
    "[Makefile]"
    "indent_style = tab"
    ""
    "[*.go]"
    "indent_style = tab"
)

$Today = Get-Date -Format "yyyy-MM-dd"

function Install-Template {
    param([string]$Source, [string]$Target)

    $targetPath = Join-Path $Destination $Target
    $targetDirectory = Split-Path -Parent $targetPath
    New-Item -ItemType Directory -Force $targetDirectory | Out-Null
    $content = Get-Content -Raw -Encoding utf8 (Join-Path $Templates $Source)
    $content = $content.Replace("<PROJECT_NAME>", $ProjectName).Replace("<YYYY-MM-DD>", $Today)
    Write-Utf8NoBom $targetPath $content
}

Install-Template "README.template.md" "README.md"
Install-Template "AGENTS.template.md" "AGENTS.md"
Install-Template "INDEX.template.md" "INDEX.md"
Install-Template "PROJECT.template.md" "PROJECT.md"

# CLAUDE.md is a portable pointer so Claude Code reads the same AGENTS.md that
# Codex and other AGENTS.md-aware tools read. A one-line @import avoids fragile
# symlinks on Windows and never duplicates instruction content.
Write-Utf8NoBom (Join-Path $Destination "CLAUDE.md") "@AGENTS.md`n"

function Add-IndexEntry {
    param([string]$Path, [string]$Purpose)
    $LinkPath = $Path -replace '\.md$', ''
    Append-Utf8NoBom (Join-Path $Destination "INDEX.md") "| [[$LinkPath|$Path]] | $Purpose |"
}

if ($Profile -ne "minimal") {
    Install-Template "DOCS_INDEX.template.md" "docs/README.md"
    Install-Template "CHANGELOG.template.md" "CHANGELOG.md"
    Install-Template "ARCHITECTURE.template.md" "docs/architecture/ARCHITECTURE.md"
    Install-Template "TESTING.template.md" "docs/quality/TESTING.md"
    Add-IndexEntry "docs/README.md" "Documentation directory index"
    Add-IndexEntry "CHANGELOG.md" "User-visible changes and releases"
    Add-IndexEntry "docs/architecture/ARCHITECTURE.md" "Current system architecture"
    Add-IndexEntry "docs/quality/TESTING.md" "Testing strategy and acceptance criteria"
}

if ($Profile -in @("operated", "all")) {
    Install-Template "ACTIONS.template.md" "ACTIONS.md"
    Install-Template "TOOLS.template.md" "TOOLS.md"
    Install-Template "INTEGRATIONS.template.md" "INTEGRATIONS.md"
    Install-Template "ENVIRONMENTS.template.md" "docs/operations/ENVIRONMENTS.md"
    Add-IndexEntry "ACTIONS.md" "Consequential actions outside git"
    Add-IndexEntry "TOOLS.md" "Non-obvious project tools and helper scripts"
    Add-IndexEntry "INTEGRATIONS.md" "External systems and integrations"
    Add-IndexEntry "docs/operations/ENVIRONMENTS.md" "Environment differences without secrets"
}

if ($Profile -eq "all") {
    Install-Template "INTERFACES.template.md" "docs/api/INTERFACES.md"
    Install-Template "DATA_MODEL.template.md" "docs/data/DATA_MODEL.md"
    Install-Template "SECURITY.template.md" "SECURITY.md"
    Install-Template "THREAT_MODEL.template.md" "docs/security/THREAT_MODEL.md"
    Add-IndexEntry "docs/api/INTERFACES.md" "Interface catalog and links to API specifications"
    Add-IndexEntry "docs/data/DATA_MODEL.md" "Data model and migration rules"
    Add-IndexEntry "SECURITY.md" "Vulnerability reporting policy"
    Add-IndexEntry "docs/security/THREAT_MODEL.md" "Threats, mitigations, and residual risks"
}

$git = Get-Command git -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $git) {
    function Invoke-GitRequired {
        param(
            [string]$Step,
            [string[]]$Arguments
        )

        $output = @(& $git.Source -C $Destination @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            $details = ($output | ForEach-Object { $_.ToString() }) -join "`n"
            if ([string]::IsNullOrWhiteSpace($details)) {
                $details = "git exited with code $exitCode"
            }
            throw "$Step failed:`n$details"
        }
    }

    Invoke-GitRequired "git init" @("init")
    Invoke-GitRequired "git symbolic-ref" @("symbolic-ref", "HEAD", "refs/heads/main")
    Invoke-GitRequired "git add" @("add", "-A")

    & $git.Source -C $Destination var GIT_AUTHOR_IDENT 2>$null | Out-Null
    $hasAuthorIdentity = $LASTEXITCODE -eq 0
    & $git.Source -C $Destination var GIT_COMMITTER_IDENT 2>$null | Out-Null
    $hasCommitterIdentity = $LASTEXITCODE -eq 0

    if (-not ($hasAuthorIdentity -and $hasCommitterIdentity)) {
        Write-Host "Initialized git repository and staged the initial state."
        Write-Host "Git identity is not configured; set user.name and user.email, then run: git commit -m 'Bootstrap project with new-project-rules'"
    }
    else {
        Invoke-GitRequired "git commit" @("commit", "-m", "Bootstrap project with new-project-rules")
        Write-Host "Initialized git repository with an initial commit."
    }
}
else {
    Write-Host "Git was not found; project files were created, but the repository was not initialized."
}

Write-Host "Created '$ProjectName' at $Destination using profile '$Profile'."
Write-Host "Open this folder as an Obsidian vault, review INDEX.md, then create its GitHub repository."
