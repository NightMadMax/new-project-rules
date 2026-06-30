# Agent Instructions

## Communication Language

- Always answer the user in Russian, including research, reviews, plans,
  progress updates, and final reports.
- Preserve commands, paths, identifiers, API names, and original error messages
  when translating them would reduce technical accuracy.
- Use another language only when the user explicitly requests it.

## Project Identity

- Project: `Правила для нового проекта`
- This folder is the git repository root and a project folder inside the parent
  Obsidian vault.
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
  without contradicting them. An `AGENTS.override.md` replaces a level entirely;
  plain `AGENTS.md` is concatenated with parent levels.
- Keep `AGENTS.md` compact: Codex truncates the instruction chain past
  `project_doc_max_bytes` (32 KiB by default). Move topic detail into `docs/`.
- Do not edit `AGENTS.md` or `CLAUDE.md` mid-session; it invalidates the cached
  prompt prefix. Record new rules between sessions.

## Rule Authoring

- Keep instruction files compact (target ~150 lines); over-long files get
  ignored from the bottom. Move detail into `docs/` or skills.
- Prefer specific negative instructions ("don't use X — use Y") and exact
  commands over prose like "write clean code".
- Lead with the most critical, non-negotiable rules and group them by task.
- State the reason, then the rule; avoid vague directives and aspirational rules
  not reflected in the codebase.
- Verify a rule sticks by asking the agent to recite it back; if it cannot, the
  file is too long or the rule is unclear.

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
  the bootstrap documentation, affected templates, related skills, and the active
  global `~/.codex/AGENTS.md` in the same task. Never update rules without
  updating the skills that implement them.

## Defect Tracking

- Every discovered defect, bug, or known issue must be recorded in
  `docs/quality/DEFECTS.md` immediately upon discovery — never leave it only in
  conversation context, commit messages, or memory.
- Each entry must include a short title, the date discovered, and a brief
  description. The current status is represented by the section where the entry
  lives: `Open`, `Fixed`, or `Won't Fix`.
- When a defect is fixed, move the entry to `Fixed` and add the fix date, commit
  reference, and root cause when known; do not delete the entry.
- Before starting work on a component, check `DEFECTS.md` for open issues in
  that area to avoid re-introducing or duplicating known problems.
- If `docs/quality/DEFECTS.md` does not exist when a defect is found, create it
  using the project defect template.

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

## Pattern Playbook

- Record a verified, reusable successful pattern in `docs/quality/PLAYBOOK.md`
  once it has proven correct at least twice — the success-side counterpart to
  the defect log, so the agent repeats the known-good approach.
- Each entry includes a short title, the date added, the component, the concrete
  known-good steps, and the evidence (commits/PRs or a passing test).
- Keep entries project-specific; propose cross-project patterns for promotion
  instead of leaving them only here. Create the file from the template the first
  time a pattern qualifies; do not pre-create it empty.

## Reflexive Learning

- After a mistake or a user correction, before moving on, reflect on the root
  cause, abstract it beyond the specific case, and record the lesson where it
  belongs: `DEFECTS.md` for a bug, `PLAYBOOK.md` for a verified good approach,
  `AGENTS.md` for a project rule (between sessions), or a promotion proposal when
  the lesson is reusable across projects.
- Record only abstractable, recurring lessons; skip one-off typos and noise.

## Verification

- Validate shell scripts with `sh -n`.
- Validate PowerShell scripts with a parser when PowerShell is available.
- Check that templates contain no absolute machine-specific paths or secrets.
