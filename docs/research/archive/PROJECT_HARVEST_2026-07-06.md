---
type: research
status: complete
owner: project
last_verified: 2026-07-06
source_of_truth: repository
related:
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY]]"
  - "[[docs/quality/PROMOTION_CANDIDATES]]"
  - "[[docs/quality/DEFECTS]]"
---

# Полный harvest соседних проектов — 2026-07-06

## Область и метод

Проверены все соседние каталоги, которые подтверждены как отдельные
git-репозитории через наличие `.git` и `git remote get-url origin`:

- `best-practices` (`NightMadMax/best-practices`);
- `Other` (`NightMadMax/Other`);
- `jira-analytics` (`NightMadMax/jira-analytics`);
- `router-watchdog-ops` (`NightMadMax/router-watchdog-ops`).

Источники просматривались read-only. Приоритет: checked-in `DEFECTS`,
`PLAYBOOK`, ADR, research, runbooks и затем `CHANGELOG`. Raw agent memory и
приватные значения не использовались как evidence. Каждый сигнал проверен на
повторяемость, очистимость и возможность реализации как rule, template, test,
validator, script, skill или guide.

## Добавлено в backlog

1. `PC-2026-625b2fcadaef` — one-file-per-candidate вместо общей таблицы.
   Реальный merge-conflict defect и ADR из `best-practices` напрямую применимы
   к текущему [[docs/quality/PROMOTION_CANDIDATES|promotion backlog]].
2. `PC-2026-4eb5666c703b` — collision-resistant candidate IDs вместо общего
   последовательного счётчика. Legacy ID должны остаться валидными.
3. `PC-2026-e6f54a0fe78a` — allowlist и redaction при диагностике
   пользовательских профилей. Инцидент из `jira-analytics` независимо
   подтверждается secret-safe реализацией global-policy sync в этом проекте.

Все три записи имеют статус `triaged`: lesson очищен и target понятен, но
пользовательского approval на перенос не было.

## Обнаруженные дефекты текущего проекта

До harvest раздел `Open` в [[docs/quality/DEFECTS]] был пуст. Структурная
сверка с доказанными дефектами `best-practices` выявила два открытых риска:

- `#43`: единая таблица backlog является merge-conflict hotspot;
- `#44`: последовательные ID конфликтуют между независимыми ветками.

Они не исправлялись этим workflow: harvest только нормализует кандидатов.

## Отфильтрованные сигналы

- `Other`: checked-in defect/playbook/research артефактов нет; доказуемых
  lessons для promotion не найдено.
- `router-watchdog-ops`: открытые дефекты `#22`, `#23`, `#24`, `#30` зависят
  от реального restore, 32-bit OpenWrt и естественных инцидентов. До закрытия
  operational verification перенос преждевременен. Target-native validation,
  atomic state publication и regression-before-deploy полезны, но evidence
  пока сосредоточен в одном operated project или уже покрыт текущим стандартом.
- `jira-analytics`: Jira field semantics, PowerShell JSON/date/alias детали и
  HTML/iOS rendering lessons технически корректны, но слишком стековые для
  базового project standard; их место — специализированная база практик.
- `jira-analytics` D-006/D-008/D-009: малые patch, повторная проверка Git state
  и `git diff --cached --check` уже покрываются текущим repository workflow
  либо общими инструментальными правилами; дубликаты не создавались.
- `best-practices`: provenance, lifecycle/evidence levels, whole-repository
  secret scan и GitHub ruleset verification уже реализованы в самом source
  project либо частично покрыты validator/threat model этого стандарта. Для
  нового кандидата нет отдельного незакрытого gap с достаточной независимой
  evidence.

## Готовность к apply

Готовых к `apply-promotion-candidate` записей нет: новые кандидаты только
`triaged`. Сначала нужен review и явный перевод выбранной записи в `approved`.
Рекомендуемый порядок review: file-per-candidate, collision-resistant ID,
secret-safe profile inspection.

## Follow-up 2026-07-06

Пользователь одобрил первые два кандидата. `PC-2026-625b2fcadaef` и
`PC-2026-4eb5666c703b` реализованы commit `b459bf3`; дефекты `#43–#44` закрыты.
`PC-2026-e6f54a0fe78a` остаётся `triaged` и требует отдельного approval.
