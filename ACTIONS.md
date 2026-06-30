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
| 2026-06-30 | Adopt global managed-policy markers | `~/.codex/AGENTS.md` | planned | Выполнить только по fingerprint-reviewed plan; rollback через timestamped backup. |
