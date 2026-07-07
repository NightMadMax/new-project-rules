---
type: review
status: complete
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/architecture/PROJECT_STANDARD_SCHEMA]]"
  - "[[docs/guides/PLAN_MIGRATIONS]]"
  - "[[docs/quality/DEFECTS]]"
---

# Phase 5 review: sequential migrations и schema 2

## Scope

Проверены `STANDARD_VERSION`, migration graph, metadata validation, managed
block parser, project/global/project-agents planners, atomic apply, tests и docs.

## Code review

- Для каждого target и каждой старой schema существует ровно один forward path.
- Legacy `0` применяет цепочку `0 → 1 → 2` одной атомарной записью.
- Existing schema `1` применяет только переход `1 → 2`.
- Metadata history обязана точно совпадать с путём; future ID блокируется.
- Managed schema `1` распознаётся как `managed_upgrade`, а future schema — как
  `unsupported_schema`.
- Backup, fingerprint, preimage recheck и unmanaged prefix/suffix сохранены.
- Missing/ambiguous paths, stale preimage, symlink и dirty trees блокируются.

Code review обнаружил и устранил возможность schema-1 metadata заранее заявить
future migration ID. Блокирующих замечаний после исправления нет.

## Verification gate

- bootstrap/contract/agent sync/migration/validator suites должны пройти;
- full NPR regression должен пройти до merge;
- CI `shell`, `powershell`, `smoke` обязателен;
- post-merge plan/apply smoke для schema-1 fixtures обязателен.

## Verdict

**Approve после полного regression и CI.** Последовательная модель сохраняет
обратную совместимость и не ослабляет atomic/fingerprint safety.
