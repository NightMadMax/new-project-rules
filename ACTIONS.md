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
| 2026-06-30 | Adopt global managed-policy markers | `~/.codex/AGENTS.md` | completed | Commit `e4dcd52`; fingerprint `05a3a369…51120`; backup `AGENTS.md.bak.20260630T004702Z`, SHA-256 `0cbba770…4f4198`; postcondition `managed_match`, repeated apply `up_to_date`. Rollback: atomic restore из backup. |
