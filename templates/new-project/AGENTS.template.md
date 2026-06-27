# Agent Instructions

## Project Identity

- Project: `<PROJECT_NAME>`
- This folder is both the Obsidian vault and git repository root.
- Project navigation: [[README]], [[INDEX]], and [[PROJECT]].

## Markdown Workflow

- Edit Markdown files directly in the project folder.
- Do not use an Obsidian REST API, helper script, synchronization step, or
  duplicate Markdown copy.
- Keep `INDEX.md` current when files change purpose or location.
- Use wikilinks for relationships between Markdown notes; code-formatted paths
  do not create Obsidian graph connections.

## Repository Workflow

- Use a separate GitHub repository for this project.
- Commit and push completed repository changes unless the user asks not to.
- Ask before pull requests, releases, issues, remote changes, or destructive
  history operations.
- Keep paths relative and account for macOS and Windows differences.

## Documentation

- Required core: `README.md`, `AGENTS.md`, `INDEX.md`, and `PROJECT.md`.
- Keep durable artifacts under `docs/`.
- Store one decision per ADR, one investigation per research file, and one code
  review per review file.
- Use `ACTIONS.md` only for consequential actions outside git.
- Do not create empty documents without a current purpose.
- Treat API specifications, lock files, generated SBOM files, and
  `.github/CODEOWNERS` as authoritative.
- Never commit secrets or real credentials.
