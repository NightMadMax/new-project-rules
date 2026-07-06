---
type: quality-backlog
status: active
owner: project
last_verified: 2026-07-06
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
| PC-2026-625b2fcadaef | triaged | `best-practices`: `docs/quality/DEFECTS.md`, `ADR-0003-one-practice-per-file.md`; `new-project-rules`: [[docs/quality/DEFECTS]] `#43` | Единая таблица кандидатов стала конфликтным shared mutable artifact при независимых PR; текущий promotion backlog использует ту же структуру. | Git-очереди, которые пополняют независимые авторы или агенты, должны хранить один элемент в одном файле, а общий README использовать только как индекс. | Репозитории с review-очередями, registries и append-oriented knowledge backlogs. | `best-practices` commit `09f3a16`, defect log и ADR-0003; структурная сверка текущего backlog 2026-07-06. | `template` | `docs/quality/promotion-candidates/`, candidate template, validator и harvest/apply skills | Очищено от project-private context. Готов к review; не approved. Миграция должна сохранить историю implemented/rejected записей и wikilinks. |
| PC-2026-4eb5666c703b | triaged | `best-practices`: `docs/quality/DEFECTS.md`, `ADR-0004-collision-resistant-candidate-ids.md`; `new-project-rules`: [[docs/quality/DEFECTS]] `#44` | Последовательный `max + 1` ID конфликтует между ветками; текущий backlog предписывает тот же формат. | Идентификаторы объектов, создаваемых независимо в Git-ветках, не должны зависеть от общего счётчика; генератор должен создавать collision-resistant ID и валидатор запрещать дубли. | Любые file-per-item очереди и registries с параллельным contribution workflow. | `best-practices` commit `7e32615`, defect log и ADR-0004; текущие ID/field guide backlog 2026-07-06. | `script` | generator candidate ID, validator и harvest/apply skills | Очищено. Готов к review; не approved. Legacy ID сохранить без переименования. |
| PC-2026-e6f54a0fe78a | triaged | `jira-analytics`: `docs/operations/agent-defect-log.md` D-004; `new-project-rules`: [[docs/security/THREAT_MODEL]], `scripts/sync_global_agents.py` | Широкий рекурсивный поиск по пользовательскому профилю вывел исторический credential из state/session-файлов; локальный secret-safe sync уже доказывает allowlist/redaction подход. | При поиске конфигурации в потенциально чувствительных профилях сначала задавать allowlist файлов и исключать state, backups, sessions и logs; диагностический вывод редактировать до отображения. | Agent tooling, интеграции и migration/diagnostic scripts, читающие пользовательские конфиги вне repository. | `jira-analytics` D-004 (2026-06-28); secret-safe structural diff и regression coverage в `new-project-rules`. | `rule` | `GLOBAL_AGENT_INSTRUCTIONS.md`, `templates/new-project/AGENTS.template.md`, policy contract/test | Очищено от credential и private paths. Готов к review; не approved. Это правило про безопасное чтение, а не замена repository-wide secret scanning. |

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
