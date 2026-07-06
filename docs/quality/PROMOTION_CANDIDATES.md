---
type: quality-backlog-index
status: active
owner: project
last_verified: 2026-07-06
source_of_truth: repository
related:
  - "[[docs/quality/promotion-candidates/README]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY]]"
  - "[[docs/quality/DEFECTS]]"
  - "[[docs/quality/PLAYBOOK]]"
---

# Promotion Candidates

Стабильная точка входа в очередь promotion. Канонические записи находятся в
каталоге [[docs/quality/promotion-candidates/README|promotion-candidates]] по
модели «один кандидат — один файл». Этот файл не содержит общей изменяемой
таблицы и не требует правки при добавлении кандидата.

## Status model

- `new` — кандидат найден, но ещё не проверен;
- `triaged` — lesson очищен и связан с target;
- `approved` — перенос явно согласован;
- `implemented` — изменение внесено и связано с commit;
- `rejected` — перенос отклонён с причиной в Notes.

## Required fields

`type: promotion-candidate`, `id`, `status`, `source`, `observation`,
`generalized_lesson`, `scope`,
`evidence`, `artifact_type`, `proposed_target`, `created`, `last_verified`.
Для `implemented` обязателен `implemented_commit`.

Новые ID создаёт `scripts/promotion_candidates.py`: формат
`PC-YYYY-<12 lowercase hex>`. Legacy ID `PC-YYYY-NNN` валидны и не
переименовываются. Validator проверяет schema, filename, status, artifact type,
даты, уникальность ID и traceability реализованных записей.
