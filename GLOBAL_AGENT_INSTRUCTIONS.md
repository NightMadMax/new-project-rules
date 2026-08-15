# Global Agent Instructions

## Communication

- Always answer the user in Russian unless they explicitly request another language.
- Preserve commands, paths, identifiers, API names, and original error messages when translation would reduce accuracy.
- Prefer the shortest response that remains clear. Use plain language instead
  of slang or unnecessary jargon.
- When a useful improvement stays within the user's task, propose it explicitly;
  do not expand the scope silently.

## Planning

- A large single-file plan is hard to review and keep consistent. Keep the main
  plan as a concise map of decisions and status; move detailed phases,
  subsystems, and large items into separate linked subplans.

## Authorization and Scope

- For analysis, diagnosis, review, or status requests, inspect and report without modifying files or external state unless the user also asks for changes.
- Keep actions inside the user's stated scope. Ask before materially expanding it or installing dependencies.
- Run relevant checks after changes; if a check was not run, state why.
- Move recurring multi-step workflows into skills instead of expanding this global file.

## Git and User Changes

- Inspect the worktree before editing and preserve unrelated user changes.
- Do not publish passwords or secrets unless the user explicitly requests it. Before the first such publication, ask the user for confirmation.
- Never run two agents concurrently in one git working copy; use separate worktrees for parallel agents.

## Tool and Dependency Selection

- Read the nearest project instructions and use the project's existing language, package manager, and toolchain first.
- Prefer the smallest standard tool that preserves correctness and portability.
- Do not install third-party dependencies without approval. Explain what is needed, why, and the installation scope first.

## Instruction Hierarchy

- Keep project rules in `AGENTS.md`; use a one-line `CLAUDE.md` import `@AGENTS.md` instead of duplicating rules or creating a symlink.
- Globally, `~/.claude/CLAUDE.md` contains only `@~/.codex/AGENTS.md`.

## New Project Defaults

- Use one shared Obsidian vault. Each project is a child folder whose root is also its git repository root, not a separate vault or synchronized copy.
- Create a separate GitHub repository for each project unless the user requests local-only, a monorepo, or another structure.
- Use the `new-project-rules` skills and templates for project documentation, defect tracking, playbooks, knowledge promotion, and machine setup; keep those project-specific processes out of global instructions.
