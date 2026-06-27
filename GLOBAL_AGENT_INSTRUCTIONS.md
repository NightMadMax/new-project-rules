# Global Agent Instructions

## New Project Default

- For any new project, use this default layout: the project folder itself is
  the Obsidian vault, and that same folder is also the git repository root.
- Only use separate repository and Obsidian copies when the user or
  project-local instructions explicitly require it.
- Create a separate GitHub repository for each new project unless the user
  explicitly requests a monorepo or another structure.

## Agent Instruction Files

- Keep `AGENTS.md` as the single source of agent rules so Codex and every other
  AGENTS.md-aware tool reads it directly.
- Make Claude Code read the same rules through a `CLAUDE.md` that contains only
  the import line `@AGENTS.md`. Use this one-line import on every OS instead of
  a symlink: it is simpler, portable, and officially supported by Claude Code.
  Never duplicate instruction content between the two files.
- Globally, point Claude Code at the Codex instructions once per machine with a
  `~/.claude/CLAUDE.md` that contains `@~/.codex/AGENTS.md`. Use
  `scripts/setup-global-agents.sh` or `.ps1` to wire this safely and
  idempotently without overwriting existing instructions.
- Keep all shared rules in the root `AGENTS.md`. When a subdirectory genuinely
  needs its own rules, add a scoped pair next to it — `services/<name>/AGENTS.md`
  with a sibling `services/<name>/CLAUDE.md` containing `@AGENTS.md` (for example
  via `scripts/add-agent-scope.sh` or `.ps1`). The nearest file in the tree wins.

## Markdown Default

- Edit Markdown files directly in the project folder. They are simultaneously
  repository files and Obsidian notes.
- Do not use an Obsidian REST API, helper script, synchronization step, or
  duplicate Markdown copy in the default single-folder layout.
- Never store tokens, passwords, private keys, or real credentials in the
  repository, documentation, scripts, or committed shell history.
- Use Obsidian wikilinks for relationships between Markdown notes. Filenames
  written only as inline code do not create graph connections.
- Make `INDEX.md` a connected navigation hub with wikilinks to project notes.

## Project Documentation Baseline

- Use a two-level model: create a small required core, then add conditional
  artifact sets only when the project needs them.
- Required core: `README.md`, `AGENTS.md`, `INDEX.md`, and `PROJECT.md`.
- Add `CHANGELOG.md` for projects with user-visible changes or releases.
- Keep durable documentation under `docs/` instead of accumulating reports in
  the repository root.
- Store current architecture in `docs/architecture/ARCHITECTURE.md` and one
  decision per file in `docs/architecture/decisions/ADR-<number>-<slug>.md`.
- Store one investigation per file in `docs/research/` and one code review per
  file in `docs/reviews/`.
- For operated projects, use `docs/operations/ENVIRONMENTS.md`, `runbooks/`,
  and `incidents/`. For executable code, use `docs/quality/TESTING.md`.
- Add API, data, security, integrations, and supply-chain documentation only
  when relevant.
- Use `ACTIONS.md` only for consequential actions outside git. Use GitHub
  Issues or the project tracker for ordinary development tasks.
- Treat API specifications, lock files, generated SBOM files, and
  `.github/CODEOWNERS` as authoritative. Markdown should explain and link to
  them, not duplicate them.
- Do not create empty placeholder documents without a current purpose.
- Prefer frontmatter with `type`, `status`, `owner`, `last_verified`,
  `source_of_truth`, and `related` when useful.
- Keep `INDEX.md` updated when files are added, removed, moved, renamed, or
  repurposed.
- Keep every project artifact inside the project root.

## Operating Rule

- Work directly with Markdown files in the project folder because that folder
  is already the Obsidian vault.
- Do not mirror files to another vault path unless the project explicitly
  documents a split-layout exception.
- When a reusable new-project convention changes, update the global agent
  instructions (`~/.codex/AGENTS.md`, mirrored to `~/.claude/CLAUDE.md`), this
  portable copy, bootstrap documentation, and affected templates in the same
  task.
