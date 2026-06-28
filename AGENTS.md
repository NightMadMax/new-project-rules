# Agent Instructions

## Communication Language

- Always answer the user in Russian, including research, reviews, plans,
  progress updates, and final reports.
- Preserve commands, paths, identifiers, API names, and original error messages
  when translating them would reduce technical accuracy.
- Use another language only when the user explicitly requests it.

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
- `AGENTS.md` is the single source of agent rules. `CLAUDE.md` only contains
  `@AGENTS.md` so Claude Code reads the same file; never duplicate rules there.
- For scoped subdirectory instructions, create an adjacent
  `AGENTS.md`/`CLAUDE.md` pair. Scoped rules must specialize broader rules
  without contradicting them.

## Repository Workflow

- Use GitHub for version control and portability between computers.
- After user-requested repository changes, commit and push to `origin/main`
  unless the user explicitly asks not to sync.
- Ask before creating pull requests, releases, issues, changing remotes, or
  performing destructive history operations.
- Keep paths relative and scripts portable across macOS and Windows.

## Tool Selection

- Use the existing project toolchain first and avoid new dependencies unless
  the user approves them.
- Prefer Python 3 standard-library code for non-trivial reusable
  cross-platform automation when Python is available on every target machine.
- Prefer `git`, `rg`, POSIX shell, or PowerShell for simple native operations.
- Retain shell and PowerShell entry points when Python cannot be assumed on a
  clean target machine.
- If a missing tool is materially better than available substitutes, explain
  the benefit and installation scope and ask the user for permission before
  installing it. Do not silently choose a lower-quality workaround.
- After approval, install through the normal package manager, verify the
  version, and document project-specific tooling in `TOOLS.md` or its manifest.

## Documentation Model

- Required core: `README.md`, `AGENTS.md`, `INDEX.md`, and `PROJECT.md`.
- Keep durable artifacts under `docs/` and reusable files under
  `templates/new-project/`.
- Keep `docs/README.md` as the index of the documentation directory.
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
