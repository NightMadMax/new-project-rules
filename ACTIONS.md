---
type: action-log
status: active
owner: project
last_verified: 2026-06-30
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
| 2026-07-02 | Re-adopt global managed-policy markers after drift | `~/.codex/AGENTS.md` | completed | Дефект 28 ([[docs/quality/DEFECTS|DEFECTS]]): активный файл был перезаписан старой редакцией без markers (`unmanaged_conflict`). Ручной user-reviewed шаг: backup `AGENTS.md.bak-2026-07-02`, копия portable policy поверх активного (`legacy_exact`); затем migration `0002`, fingerprint `18a73ff1…f063d`, engine backup `AGENTS.md.bak.20260702T151955Z`; postcondition `managed_match`. Root cause до конца не установлен — проверить второй компьютер на старый `setup-global-agents`. Rollback: atomic restore из backup. |
| 2026-06-30 | Adopt global managed-policy markers | `~/.codex/AGENTS.md` | completed | Commit `e4dcd52`; fingerprint `05a3a369…51120`; backup `AGENTS.md.bak.20260630T004702Z`, SHA-256 `0cbba770…4f4198`; postcondition `managed_match`, repeated apply `up_to_date`. Rollback: atomic restore из backup. |
| 2026-06-30 | Audit/apply default-branch protection | GitHub `NightMadMax/new-project-rules` | blocked | Rulesets и classic branch protection APIs вернули `403`: private repo требует GitHub Pro либо public visibility. State не изменён; повторить после смены plan/visibility. |
| 2026-06-30 | Verify workflow token defaults | GitHub `NightMadMax/new-project-rules` | completed | API: `default_workflow_permissions=read`, `can_approve_pull_request_reviews=false`; изменение не требовалось. |
| 2026-06-30 | Enforce GitHub Actions supply-chain policy | GitHub `NightMadMax/new-project-rules` | completed | API postcondition: `allowed_actions=selected`, `sha_pinning_required=true`, `github_owned_allowed=true`, `verified_allowed=false`, empty custom patterns. Rollback: restore `allowed_actions=all`, `sha_pinning_required=false`. |
