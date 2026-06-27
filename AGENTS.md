# Agent Instructions

## Project Identity

- Project: `Правила для нового проекта`
- This folder is both the Obsidian vault and git repository root.
- Project navigation: [[README]], [[INDEX]], [[PROJECT]], and [[TEMPLATES]].

## Markdown Workflow

- Edit Markdown files directly in this project folder.
- Do not use an Obsidian REST API, helper script, synchronization step, or
  duplicate Markdown copy.
- Keep `INDEX.md` updated when a file is added, removed, moved, renamed, or
  repurposed.
- Use wikilinks for relationships between Markdown notes; code-formatted paths
  do not create Obsidian graph connections.

## Repository Workflow

- Use GitHub for version control and portability between computers.
- After user-requested repository changes, commit and push to `origin/main`
  unless the user explicitly asks not to sync.
- Ask before creating pull requests, releases, issues, changing remotes, or
  performing destructive history operations.
- Keep paths relative and scripts portable across macOS and Windows.

## Documentation Model

- Required core: `README.md`, `AGENTS.md`, `INDEX.md`, and `PROJECT.md`.
- Keep durable artifacts under `docs/` and reusable files under
  `templates/new-project/`.
- Store one decision per ADR, one investigation per research file, and one code
  review per review file.
- Do not create empty project documents without a current purpose.
- Treat machine-readable API specifications, lock files, generated SBOM files,
  and `.github/CODEOWNERS` as authoritative.
- Never commit secrets, tokens, private keys, passwords, or real credentials.
- When these reusable conventions change, update `GLOBAL_AGENT_INSTRUCTIONS.md`,
  the bootstrap documentation, affected templates, and the active global
  `~/.codex/AGENTS.md` in the same task.

## Verification

- Validate shell scripts with `sh -n`.
- Validate PowerShell scripts with a parser when PowerShell is available.
- Check that templates contain no absolute machine-specific paths or secrets.
