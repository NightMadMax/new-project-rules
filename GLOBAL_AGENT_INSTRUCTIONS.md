# Global Agent Instructions

## Communication

- Always answer the user in Russian unless they explicitly request another language.
- Preserve commands, paths, identifiers, API names, and original error messages when translation would reduce accuracy.

## Authorization and Scope

- For analysis, diagnosis, review, or status requests, inspect and report without modifying files or external state unless the user also asks for changes.
- Keep actions inside the user's stated scope. Ask before materially expanding it or installing dependencies.
- Run relevant checks after changes; if a check was not run, state why.
- Move recurring multi-step workflows into skills instead of expanding this global file.

## Git and User Changes

- Inspect the worktree before editing and preserve unrelated user changes.
- Do not commit, push, open pull requests, create releases or issues, change remotes, or rewrite history unless the user explicitly requests it or project-local instructions require that repository workflow.
- Never run two agents concurrently in one git working copy; use separate worktrees for parallel agents.

## Tool and Dependency Selection

- Read the nearest project instructions and use the project's existing language, package manager, and toolchain first.
- Prefer the smallest standard tool that preserves correctness and portability.
- Do not install third-party dependencies without approval. Explain what is needed, why, and the installation scope first.
- Never store secrets, tokens, passwords, private keys, or real credentials in repositories, documentation, scripts, or committed shell history.

## Instruction Hierarchy

- Keep project rules in `AGENTS.md`; use a one-line `CLAUDE.md` import `@AGENTS.md` instead of duplicating rules or creating a symlink.
- Globally, `~/.claude/CLAUDE.md` contains only `@~/.codex/AGENTS.md`.
- Root instructions define shared rules. A nearer `AGENTS.md` specializes or overrides them for its subtree; `AGENTS.override.md` deliberately replaces the instruction file at that directory level.
- Keep instruction files concise. Codex stops adding files when the combined instruction chain reaches `project_doc_max_bytes` (32 KiB by default); move detailed workflows into docs or skills.
- Instruction-file changes apply to new sessions. After changing them, start a new session and verify the loaded instruction sources, for example with `codex --ask-for-approval never "Summarize the current instructions."` and `codex --cd <directory> ...` for nested scopes.

## New Project Defaults

- Use one shared Obsidian vault. Each project is a child folder whose root is also its git repository root, not a separate vault or synchronized copy.
- Create a separate GitHub repository for each project unless the user requests local-only, a monorepo, or another structure.
- Use the `new-project-rules` skills and templates for project documentation, defect tracking, playbooks, knowledge promotion, and machine setup; keep those project-specific processes out of global instructions.
