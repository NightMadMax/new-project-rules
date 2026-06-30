# Global Agent Instructions

## Communication Language

- Always answer the user in Russian, including research, reviews, plans,
  progress updates, and final reports.
- Preserve commands, paths, identifiers, API names, and original error messages
  when translating them would reduce technical accuracy.
- Use another language only when the user explicitly requests it.

## New Project Default

- Use one shared Obsidian workspace folder as the vault. Create each new
  project as a child folder inside that vault; the project folder is the git
  repository root, but not a separate Obsidian vault.
- Keep Markdown in the project folder so the parent vault indexes it directly.
  Do not create a second Obsidian copy or synchronization layer.
- Put a project outside the shared vault only when the user or project-local
  instructions explicitly require it.
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
  via `scripts/add-agent-scope.sh` or `.ps1`). Nested rules must specialize the
  root rules without contradicting them. Both agents combine instruction layers;
  a nearer file is loaded later but does not erase broader instructions.
- Keep `AGENTS.md` compact. Codex stops appending the instruction chain once it
  exceeds `project_doc_max_bytes` (32 KiB by default), so a long or verbose file
  is silently truncated. Prefer short, specific rules and move topic detail into
  `docs/`.
- An `AGENTS.md` is concatenated with parent levels, but an `AGENTS.override.md`
  at a level replaces that level entirely instead of extending it. Use plain
  `AGENTS.md` to add rules; use `*.override.md` only to deliberately replace
  them.
- Do not edit `AGENTS.md` or `CLAUDE.md` in the middle of an agent session: it
  invalidates the cached prompt prefix and wastes tokens. Record a new rule
  between sessions, promoting it from a recurring defect or a confirmed practice.

## Rule Authoring

- Keep instruction files compact (target ~150 lines); over-long files get
  ignored from the bottom. Move detail into `docs/` or skills.
- Prefer specific negative instructions ("don't use X — use Y") and exact
  commands over prose like "write clean code".
- Lead with the most critical, non-negotiable rules and group them by task
  ("When writing code", "When reviewing", "When releasing").
- State the reason, then the rule; avoid vague directives ("be careful") and
  aspirational rules not reflected in the codebase.
- Verify a rule sticks by asking the agent to recite it back; if it cannot, the
  file is too long or the rule is unclear.

## Tool Selection

- Use the project's existing language, package manager, and toolchain before
  introducing another runtime.
- Prefer standard tools already available on every target machine and avoid
  new third-party dependencies unless the user approves them.
- For non-trivial reusable automation that must behave consistently on macOS
  and Windows, prefer Python 3 with the standard library when Python is known
  to be available on all target machines. Document the minimum Python version.
- For simple local file, process, and git operations, prefer the smallest
  suitable native tool such as `git`, `rg`, POSIX shell, or PowerShell rather
  than adding a Python script.
- Keep POSIX shell and Windows PowerShell wrappers when a clean target machine
  cannot be assumed to have Python.
- If a clearly better-suited tool is missing and using an available substitute
  would materially reduce correctness, reproducibility, maintainability, or
  verification quality, do not silently use the weaker workaround. Explain
  what tool is needed, why it is preferable, what will be installed, and ask
  the user for permission before installation.
- Do not request or perform an installation for a marginal convenience when an
  available standard tool provides equivalent quality.
- After approval, install through the platform or project package manager,
  verify the installed version, and document project-specific tooling in
  `TOOLS.md` or the appropriate manifest without recording secrets.

## Markdown Default

- Edit Markdown files directly in the project folder. They are simultaneously
  repository files and Obsidian notes.
- Do not use an Obsidian REST API, helper script, synchronization step, or
  duplicate Markdown copy in the default parent-vault layout.
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

## Defect Tracking

- Every discovered defect, bug, or known issue must be recorded in
  `docs/quality/DEFECTS.md` immediately upon discovery — never leave it only in
  conversation context, commit messages, or memory.
- Each entry must include: a short title, current status (`open` / `fixed` /
  `wontfix`), the date discovered, a brief description, and the root cause when
  known.
- When a defect is fixed, update its status and add the fix date and commit
  reference; do not delete the entry.
- Before starting work on a component, check `DEFECTS.md` for open issues in
  that area to avoid re-introducing or duplicating known problems.
- If `docs/quality/DEFECTS.md` does not exist when a defect is found, create it
  using the project defect template.
- When `docs/` exists, maintain `docs/README.md` as its connected documentation
  index.
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

## Pattern Playbook

- Record a verified, reusable successful pattern in `docs/quality/PLAYBOOK.md`
  once it has proven correct at least twice — the success-side counterpart to
  the defect log, so the agent repeats the known-good approach instead of
  rediscovering it.
- Each entry includes a short title, the date added, the component, the concrete
  known-good steps, and the evidence (commits/PRs or a passing test).
- Keep playbook entries project-specific. When a pattern is reusable across
  projects and free of private context, propose it for Knowledge Promotion
  instead of leaving it only in the project.
- Create `docs/quality/PLAYBOOK.md` from the project template the first time a
  pattern qualifies; do not pre-create it empty.

## Reflexive Learning

- After a mistake or a user correction, before moving on, reflect on the root
  cause, abstract it beyond the specific case, and record the lesson where it
  belongs: `docs/quality/DEFECTS.md` for a bug, `docs/quality/PLAYBOOK.md` for a
  verified good approach, `AGENTS.md` for a project rule (between sessions, not
  mid-session), or a promotion proposal when the lesson is reusable across
  projects.
- Record only abstractable, recurring lessons; skip one-off typos and noise so
  the defect log and playbook stay signal-dense.

## Knowledge Promotion

- Keep project-specific facts, architecture, defects, decisions, research, and
  operational knowledge in the project where they originated.
- Treat Codex and Claude generated memory as local working state, not as a
  version-controlled source of truth. Never commit raw memory directories.
- Promote a lesson into `new-project-rules` only when it is reusable across
  projects, independent of private business context, and expressible as a rule,
  template, test, validator, script, or skill.
- Before promotion, record the source project or artifact, supporting evidence,
  intended scope, and verification date. Remove secrets, personal data, private
  identifiers, and machine-specific paths.
- Preserve the original project record. Promote an abstracted conclusion rather
  than copying raw incident, defect, conversation, or memory text.
- When applicability is uncertain, keep the knowledge in the source project and
  propose promotion for user review instead of changing the shared standard.

## Operating Rule

- Work directly with Markdown files in the project folder; the parent Obsidian
  vault indexes those same files.
- Do not turn each project into a separate vault and do not mirror files to a
  second vault path.
- When a reusable new-project convention changes, update the global agent
  instructions (`~/.codex/AGENTS.md`, imported by `~/.claude/CLAUDE.md`), this
  portable copy, bootstrap documentation, affected templates, and all related
  skills in the same task. Never update rules without updating the skills that
  implement them.
