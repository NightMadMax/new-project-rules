---
type: action-log
status: active
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/guides/PLAN_MIGRATIONS]]"
  - "[[docs/guides/SYNC_GLOBAL_AGENTS]]"
---

# Внешние действия

Здесь фиксируются только значимые действия вне Git. Обычные изменения кода и
документации остаются в commit history.

| Date | Action | Target | Status | Evidence / rollback |
|---|---|---|---|---|
| 2026-07-14 | Verify reviewed Admin bypass and sole owner-admin invariant | GitHub `NightMadMax/new-project-rules`, `NightMadMax/best-practices` | completed | Full read-only API audit through user `gh`: active rulesets `18603924`/`18538769`, `RepositoryRole id=5` `always`, guards/checks preserved; sole Admin is owner `NightMadMax`. Scheduled jobs use repository-scoped self-audit because `GITHUB_TOKEN` cannot inspect another repository and redacts role ID. No remote governance state changed. |
| 2026-07-07 | Refresh global policy verification command | `~/.codex/AGENTS.md` | completed | Follow-up migration `0002+0005`, reviewed fingerprint `286ce563…5d332e`; backup `AGENTS.md.bak.20260707T194042Z`, SHA-256 `f959b16b…db747b`; final postcondition `managed_match`, active SHA-256 `08708005…25186e`. New `codex exec` process `019f3e18-e9eb-7ca1-aa08-c12e5f0fe2c9` loaded and summarized the expected global and project instruction chain. Rollback: atomic restore from the timestamped backup. |
| 2026-07-07 | Refresh global managed policy after scope audit | `~/.codex/AGENTS.md` | completed | Migration `0002+0005`, reviewed fingerprint `ae4a71ab…ab86e`; engine backup `AGENTS.md.bak.20260707T193935Z`, SHA-256 `182c569e…156d45`; active postcondition `managed_match`, active SHA-256 `f959b16b…db747b`. Rollback: atomic restore from the timestamped backup. |
| 2026-07-07 | Upgrade global managed policy to schema 2 | `~/.codex/AGENTS.md` | completed | Migration `0005-upgrade-global-managed-block-v2`, reviewed fingerprint `bb3933b5…7d518`; engine backup `AGENTS.md.bak.20260707T151416Z`, SHA-256 `5397391f…fc62`; active postcondition `managed_match`, active SHA-256 `182c569e…6d45`. Rollback: atomic restore from the timestamped backup. |
| 2026-07-07 | Enable default-branch ruleset | GitHub `NightMadMax/new-project-rules` | completed | Active ruleset `Protect main`, id `18603924`: PR, one approval, Code Owner review, stale-review dismissal, thread resolution, strict checks `shell`/`powershell`, deletion/non-fast-forward block; API postcondition `main.protected=true`. Prerequisite CODEOWNERS merged через PR №2 (`4a9c1f8`). Rollback: disable or delete ruleset `18603924` через GitHub repository settings/API. |
| 2026-07-03 | Refresh managed block after package B rule updates | `~/.codex/AGENTS.md` | completed | Пакет B аудита 2026-07: portable policy получила бюджет цепочки инструкций, правило git worktrees и консолидацию формулировок, state стал `managed_drift`. Ручной шаг по паттерну engine ([[docs/quality/PLAYBOOK|PLAYBOOK]] № 1): backup `AGENTS.md.bak.20260702T220018Z` (SHA-256 `78fa7ee3…8743d2`), desired text через `sync_global_agents.desired_text` (prefix/suffix сохранены), atomic replace; postcondition `managed_match`, новый SHA-256 `960c2037…07eb13`. Rollback: atomic restore из backup. |
| 2026-07-02 | Refresh managed block on second computer after `managed_drift` | `~/.codex/AGENTS.md` (второй компьютер) | completed | Продолжение дефекта 28: managed block содержал редакцию 2026-06-30 (151 строка, SHA-256 `0cbba770…4f4198`), portable policy выросла до 200 строк. Migration engine блокирует `managed_drift`, поэтому user-approved ручной шаг по паттерну engine: backup `AGENTS.md.bak.20260702T153050Z` (SHA-256 `129d1be2…907c94`), desired text через `sync_global_agents.desired_text` (prefix/suffix сохранены), atomic replace; postcondition `managed_match`. Root cause проверен: текущий `setup-global-agents.ps1` существующий файл не перезаписывает. Rollback: atomic restore из backup. |
| 2026-07-02 | Re-adopt global managed-policy markers after drift | `~/.codex/AGENTS.md` | completed | Дефект 28 ([[docs/quality/DEFECTS|DEFECTS]]): активный файл был перезаписан старой редакцией без markers (`unmanaged_conflict`). Ручной user-reviewed шаг: backup `AGENTS.md.bak-2026-07-02`, копия portable policy поверх активного (`legacy_exact`); затем migration `0002`, fingerprint `18a73ff1…f063d`, engine backup `AGENTS.md.bak.20260702T151955Z`; postcondition `managed_match`. Root cause до конца не установлен — проверить второй компьютер на старый `setup-global-agents`. Rollback: atomic restore из backup. |
| 2026-06-30 | Adopt global managed-policy markers | `~/.codex/AGENTS.md` | completed | Commit `e4dcd52`; fingerprint `05a3a369…51120`; backup `AGENTS.md.bak.20260630T004702Z`, SHA-256 `0cbba770…4f4198`; postcondition `managed_match`, repeated apply `up_to_date`. Rollback: atomic restore из backup. |
| 2026-06-30 | Audit/apply default-branch protection | GitHub `NightMadMax/new-project-rules` | blocked | Rulesets и classic branch protection APIs вернули `403`: private repo требует GitHub Pro либо public visibility. State не изменён; повторить после смены plan/visibility. |
| 2026-06-30 | Verify workflow token defaults | GitHub `NightMadMax/new-project-rules` | completed | API: `default_workflow_permissions=read`, `can_approve_pull_request_reviews=false`; изменение не требовалось. |
| 2026-06-30 | Enforce GitHub Actions supply-chain policy | GitHub `NightMadMax/new-project-rules` | completed | API postcondition: `allowed_actions=selected`, `sha_pinning_required=true`, `github_owned_allowed=true`, `verified_allowed=false`, empty custom patterns. Rollback: restore `allowed_actions=all`, `sha_pinning_required=false`. |
