# Agent Instructions

## Project Identity

- Project: `<PROJECT_NAME>`
- This folder is the git repository root and a project folder inside the parent
  Obsidian vault.
- Project navigation: [[README]], [[INDEX]], and [[PROJECT]].

## Commands

Add only commands verified in this repository. When setting the project up,
inspect its manifests and configuration to fill in the real install, build,
test, lint, and run commands. Delete this section if the project has none.

## Done when

State the project's definition of done so the agent can self-verify before
reporting completion: which checks must pass (tests, lint, build), what counts
as a verified change, and any required review or approval. List concrete,
checkable conditions. Delete this section until the project has real criteria.

## Standard baseline

The block below is the shared new-project-rules baseline. It is managed by
migrations — do not edit between the markers. Add this project's own rules in the
sections above (or in a scoped `AGENTS.md` in a subdirectory); local rules are
never overwritten by a baseline update.

<!-- new-project-rules:begin schema=<SCHEMA_VERSION> -->
## Communication Language

- Always answer the user in Russian, including research, reviews, plans,
  progress updates, and final reports.
- Preserve commands, paths, identifiers, API names, and original error messages
  when translating them would reduce technical accuracy.
- Use another language only when the user explicitly requests it.

## Markdown Workflow

- Edit Markdown files directly in the project folder.
- Do not use an Obsidian REST API, helper script, synchronization step, or
  duplicate Markdown copy.
- `AGENTS.md` is the single source of agent rules. `CLAUDE.md` only contains
  `@AGENTS.md` so Claude Code reads the same file; keep all rules in `AGENTS.md`.
- If a subdirectory needs scoped instructions, create an adjacent
  `AGENTS.md`/`CLAUDE.md` pair. Scoped rules must specialize broader rules
  without contradicting them. An `AGENTS.override.md` replaces a level entirely;
  plain `AGENTS.md` is concatenated with parent levels.
- Keep `AGENTS.md` compact: Codex truncates the instruction chain past
  `project_doc_max_bytes` (32 KiB by default). Move topic detail into `docs/`.
- Do not edit `AGENTS.md` or `CLAUDE.md` mid-session; it invalidates the cached
  prompt prefix. Record new rules between sessions.
- Keep `INDEX.md` current when files change purpose or location.
- Use wikilinks for relationships between Markdown notes; code-formatted paths
  do not create Obsidian graph connections.

## Rule Authoring

- Keep instruction files compact (target ~150 lines); over-long files get
  ignored from the bottom. Move detail into `docs/` or skills.
- Budget the whole chain: global plus project rules together must stay within
  ~300 non-empty lines; the shared `validate-project` check warns past it.
- Prefer specific negative instructions ("don't use X — use Y") and exact
  commands over prose like "write clean code".
- Lead with the most critical, non-negotiable rules and group them by task.
- State the reason, then the rule; avoid vague directives and aspirational rules
  not reflected in the codebase.
- Verify a rule sticks by asking the agent to recite it back; if it cannot, the
  file is too long or the rule is unclear.

## Repository Workflow

- Use a separate GitHub repository for this project.
- Commit and push completed repository changes unless the user asks not to.
- Ask before pull requests, releases, issues, remote changes, or destructive
  history operations.
- Keep paths relative and account for macOS and Windows differences.
- Never run two agents at the same time in this working copy; parallel agents
  belong in separate git worktrees.

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

## Best Practices

- When the project's stack becomes clear, offer to pull matching practices from
  the sibling Best Practices base: read
  `../Best Practices/.agents/skills/apply-best-practices/SKILL.md` and follow it
  for that stack. If the base is absent, offer to clone it first, as a sibling
  in the vault (`git clone git@github.com:NightMadMax/best-practices.git
  "../Best Practices"`).
- Everything is opt-in. Record the decision in `.best-practices.json` (`optout`
  when the user declines, `applied` for delivered sections) and do not re-offer
  a declined or already-applied section.

## Knowledge Promotion

- Keep project-specific facts, architecture, defects, decisions, research, and
  operational knowledge in this project.
- Treat Codex and Claude generated memory as local working state. Never commit
  raw memory directories.
- Share a reusable engineering practice (how to build well for a stack, tool, or
  prompt) as a candidate to the sibling Best Practices base via pull request,
  not into this standard. Record the source and evidence; remove secrets,
  personal data, private identifiers, and machine-specific paths.
- The shared `new-project-rules` standard is maintainer-authored and read-only
  for users; changing it is a maintainer-only act that hardens an accepted Best
  Practices practice into a rule, template, test, validator, script, or skill.
- A defect in the standard's own tooling is an ordinary issue or pull request,
  not a knowledge promotion.
- For a cross-cutting engineering rule (secrets out of the repository, portable
  scripts, tool choice), keep the imperative here and its rationale in Best
  Practices; do not copy the rationale.

## Defect Tracking

- Record every discovered defect, bug, or known issue in
  `docs/quality/DEFECTS.md` immediately upon discovery.
- Include a short title, discovery date, and description. Status is represented
  by the section where the entry lives: `Open`, `Fixed`, or `Won't Fix`.
- When fixed, move the entry to `Fixed` and add the fix date, commit reference,
  and root cause when known.
- Check existing open defects before changing the affected component.
- If the defect log does not exist, create it from the shared project template.

## Pattern Playbook

- Record a verified, reusable successful pattern in `docs/quality/PLAYBOOK.md`
  once it has proven correct at least twice — the success-side counterpart to
  the defect log, so the agent repeats the known-good approach.
- Each entry includes a short title, the date added, the component, the concrete
  known-good steps, and the evidence (commits/PRs or a passing test).
- Keep entries project-specific; propose cross-project patterns for promotion.
  Create the file from the template the first time a pattern qualifies; do not
  pre-create it empty.

## Reflexive Learning

- After a mistake or a user correction, before moving on, reflect on the root
  cause, abstract it beyond the specific case, and record the lesson where it
  belongs: `DEFECTS.md` for a bug, `PLAYBOOK.md` for a verified good approach,
  `AGENTS.md` for a project rule (between sessions), or a promotion proposal when
  the lesson is reusable across projects.
- Record only abstractable, recurring lessons; skip one-off typos and noise.
<!-- new-project-rules:end -->
