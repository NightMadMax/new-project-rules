---
type: quality-backlog
status: active
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY]]"
  - "[[docs/quality/DEFECTS]]"
  - "[[docs/quality/PLAYBOOK]]"
---

# Promotion Candidates

Очередь кандидатов на перенос знаний из других проектов в общий стандарт
`new-project-rules`.

Этот журнал не является source of truth для исходного проекта и не заменяет
его `DEFECTS`, `PLAYBOOK`, ADR, research или runbook. Он хранит только
нормализованные, очищенные от приватного контекста кандидаты на promotion.

## Status model

- `new` — кандидат автоматически или вручную найден, но ещё не проверен.
- `triaged` — кандидат разобран, нормализован и сопоставлен с целевым типом
  артефакта.
- `approved` — пользователь или maintainers согласовали перенос.
- `implemented` — изменение внесено в репозиторий и связано с commit.
- `rejected` — перенос отклонён; причина фиксируется в Notes.

## Entry format

| ID | Status | Source | Observation | Generalized Lesson | Scope | Evidence | Artifact Type | Proposed Target | Notes |
|---|---|---|---|---|---|---|---|---|---|
| PC-2026-001 | implemented | `new-project-rules`: [[docs/quality/DEFECTS]] entries `#25` and `#27` | После исправления defect-tracking contract часть связанных rule layers и templates осталась на старой формулировке, что снова создало risk of drift. | Когда меняется reusable rule contract, изменение нужно закреплять не только в одном rules file, а во всех производных слоях и удерживать автоматической проверкой coverage. | Все проекты, где один стандарт разворачивается в несколько rule layers, templates, guides или agent bridges. | `docs/quality/DEFECTS.md` entries `#25`, `#27`; commits `97ae46f`, `fb079d3`; enhanced `scripts/test-skills.*` literal coverage for mirrored rule blocks. | `test` | `scripts/test-skills.sh`, `scripts/test-skills.ps1` | Реализовано: shell и PowerShell skill checks теперь требуют обязательные policy literals для mirrored rule contracts в `AGENTS.md`, `GLOBAL_AGENT_INSTRUCTIONS.md` и `templates/new-project/AGENTS.template.md`. |

### Field guide

- **ID** — стабильный идентификатор, например `PC-2026-001`.
- **Status** — одно из значений status model.
- **Source** — проект и исходный артефакт, без копирования приватного текста.
- **Observation** — проверенный наблюдаемый факт из источника.
- **Generalized Lesson** — обобщённый кросс-проектный вывод.
- **Scope** — каким типам будущих проектов это полезно.
- **Evidence** — defect, test, research, commit, PR или воспроизводимый опыт.
- **Artifact Type** — `rule`, `template`, `test`, `validator`, `script`,
  `skill`, `guide`.
- **Proposed Target** — конкретный файл или каталог в `new-project-rules`.
- **Notes** — причина approval/rejection, commit, follow-up или ограничения.

## Workflow

1. `harvest-project-lessons` ищет и добавляет/обновляет кандидатов со статусом
   `new` или `triaged`.
2. После review кандидат переводится в `approved` или `rejected`.
3. `apply-promotion-candidate` берёт один `approved` кандидат и переносит урок в
   конкретные артефакты репозитория.
4. После проверки и commit запись получает `implemented` и ссылку на commit.

## Rules

- Не переносить сюда raw memory, chat transcripts и сырые incident notes.
- Не дублировать здесь полный текст исходного дефекта или playbook entry;
  сохранять только краткую карточку и ссылку на источник.
- Не использовать статус `approved`, если ещё не понятен целевой артефакт.
- Если урок оказался проектно-специфичным, фиксировать `rejected` с причиной,
  а знание оставлять в исходном проекте.
