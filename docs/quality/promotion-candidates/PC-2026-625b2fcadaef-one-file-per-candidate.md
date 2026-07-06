---
type: promotion-candidate
id: PC-2026-625b2fcadaef
status: implemented
source: "best-practices defect log and ADR-0003; new-project-rules DEFECTS #43"
observation: "Единая таблица кандидатов стала конфликтным shared mutable artifact при независимых PR."
generalized_lesson: "Git-очередь независимых авторов должна хранить один элемент в одном файле, а README использовать только как индекс."
scope: "Review queues, registries и append-oriented knowledge backlogs."
evidence: "best-practices commit 09f3a16 and structural verification of the current backlog"
artifact_type: template
proposed_target: "docs/quality/promotion-candidates, validator and harvest/apply skills"
created: 2026-07-06
last_verified: 2026-07-06
implemented_commit: b459bf3
---

# Один файл на promotion candidate

## Notes

Одобрено пользователем 2026-07-06. Реализовано каталогом one-file-per-item,
стабильным index, schema validator и синхронизированными skills. Legacy-записи
и ссылки сохранены.
