# Agent Instructions

## Communication Language

- Always answer the user in Russian, including research, reviews, plans,
  progress updates, and final reports.
- Preserve commands, paths, identifiers, API names, and original error messages
  when translating them would reduce technical accuracy.
- Use another language only when the user explicitly requests it.

## Project Identity

- Project: `<PROJECT_NAME>`
- This folder is the git repository root and a project folder inside the parent
  Obsidian vault.
- Project navigation: [[README]], [[INDEX]], and [[PROJECT]].

## Commands

Add only commands verified in this repository. When setting the project up,
inspect its manifests and configuration to fill in the real install, build,
test, lint, and run commands. Delete this section if the project has none.

## Markdown Workflow

- Edit Markdown files directly in the project folder.
- Do not use an Obsidian REST API, helper script, synchronization step, or
  duplicate Markdown copy.
- `AGENTS.md` is the single source of agent rules. `CLAUDE.md` only contains
  `@AGENTS.md` so Claude Code reads the same file; keep all rules in `AGENTS.md`.
- If a subdirectory needs scoped instructions, create an adjacent
  `AGENTS.md`/`CLAUDE.md` pair. Scoped rules must specialize broader rules
  without contradicting them.
- Keep `INDEX.md` current when files change purpose or location.
- Use wikilinks for relationships between Markdown notes; code-formatted paths
  do not create Obsidian graph connections.

## Repository Workflow

- Use a separate GitHub repository for this project.
- Commit and push completed repository changes unless the user asks not to.
- Ask before pull requests, releases, issues, remote changes, or destructive
  history operations.
- Keep paths relative and account for macOS and Windows differences.

## Tool Selection

- Use the project's existing language and toolchain first.
- Prefer standard tools already available on all target machines; ask before
  adding third-party dependencies.
- Prefer Python 3 standard-library code for non-trivial reusable
  cross-platform automation when Python is available everywhere it must run.
- Prefer `git`, `rg`, POSIX shell, or PowerShell for simple native operations.
- Keep shell and PowerShell wrappers when Python cannot be assumed on a clean
  target machine.
- If a missing tool is materially better than available substitutes, explain
  what is needed and why, then ask the user for permission before installing
  it instead of silently using a lower-quality workaround.
- After approval, install through the normal package manager, verify the
  version, and document project-specific tooling in `TOOLS.md` or its manifest.

## Documentation

- Required core: `README.md`, `AGENTS.md`, `INDEX.md`, and `PROJECT.md`.
- Keep durable artifacts under `docs/`.
- When `docs/` exists, keep `docs/README.md` as its connected index.
- Store one decision per ADR, one investigation per research file, and one code
  review per review file.
- Use `ACTIONS.md` only for consequential actions outside git.
- Do not create empty documents without a current purpose.
- Treat API specifications, lock files, generated SBOM files, and
  `.github/CODEOWNERS` as authoritative.
- Never commit secrets or real credentials.

## Knowledge Promotion

- Keep project-specific facts, architecture, defects, decisions, research, and
  operational knowledge in this project.
- Treat Codex and Claude generated memory as local working state. Never commit
  raw memory directories.
- Promote a lesson into the shared `new-project-rules` standard only when it is
  reusable across projects, independent of private context, and can become a
  rule, template, test, validator, script, or skill.
- Record the source artifact, evidence, intended scope, and verification date;
  remove secrets, personal data, private identifiers, and machine-specific paths.
- Preserve the original record and promote an abstracted conclusion, not raw
  incident, defect, conversation, or memory text.
- When applicability is uncertain, keep the knowledge here and ask the user
  before changing the shared standard.

## Defect Tracking

- Record every discovered defect, bug, or known issue in
  `docs/quality/DEFECTS.md` immediately upon discovery.
- Include a short title, status (`open` / `fixed` / `wontfix`), discovery date,
  description, and root cause when known.
- When fixed, keep the entry and add the fix date and commit reference.
- Check existing open defects before changing the affected component.
- If the defect log does not exist, create it from the shared project template.
