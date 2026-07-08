---
type: promotion-candidate
id: PC-2026-4eb5666c703b
status: implemented
source: "best-practices defect log and ADR-0004; new-project-rules DEFECTS #44"
observation: "Последовательный max-plus-one ID конфликтует между независимыми Git-ветками."
generalized_lesson: "ID параллельно создаваемых Git-объектов не должен зависеть от общего счётчика; генератор создаёт collision-resistant ID, validator запрещает дубли."
scope: "File-per-item queues и registries с параллельным contribution workflow."
evidence: "best-practices commit 7e32615 and the previous sequential backlog contract"
artifact_type: script
proposed_target: "scripts/promotion_candidates.py, validator and harvest/apply skills"
created: 2026-07-06
last_verified: 2026-07-06
implemented_commit: b459bf3
---

# Collision-resistant promotion candidate IDs

## Notes

Одобрено пользователем 2026-07-06. Реализованы 48-битный random suffix,
локальный collision retry, duplicate validator и regression tests. Legacy ID
сохраняются без переименования.
