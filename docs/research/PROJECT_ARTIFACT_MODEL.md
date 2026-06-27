---
type: research
status: accepted
owner: project
last_verified: 2026-06-27
source_of_truth: repository
related:
  - "[[PROJECT]]"
  - "[[INDEX]]"
  - "[[docs/architecture/ARCHITECTURE|ARCHITECTURE]]"
  - "[[docs/architecture/decisions/ADR-0001-two-level-documentation|ADR-0001]]"
---

# Модель артефактов проекта

| Условие | Артефакт |
|---|---|
| Любой проект | [[README]], [[AGENTS]], [[INDEX]], [[PROJECT]] |
| Есть релизы | [[CHANGELOG]] |
| Есть значимые технические решения | [[templates/new-project/ADR.template|ADR template]] |
| Есть исполняемый код | [[docs/architecture/ARCHITECTURE|ARCHITECTURE]], [[templates/new-project/TESTING.template|TESTING template]] |
| Есть внешние операции | [[templates/new-project/ACTIONS.template|ACTIONS template]] |
| Есть production/устройства | `docs/operations/` |
| Есть API | [[templates/new-project/INTERFACES.template|INTERFACES template]] и API-spec |
| Есть постоянные данные | `docs/data/` |
| Есть чувствительные активы | [[templates/new-project/SECURITY.template|SECURITY template]], `docs/security/` |
| Есть внешние сервисы | [[templates/new-project/INTEGRATIONS.template|INTEGRATIONS template]] |
| Есть необычные инструменты | [[templates/new-project/TOOLS.template|TOOLS template]] |

Разделение строится не по формату, а по жизненному циклу информации:

- текущее состояние системы — архитектура и интерфейсы;
- причины выбора — ADR;
- проверяемые гипотезы — исследования;
- воспроизводимые действия — runbook;
- произошедшие сбои — postmortem;
- пользовательские изменения — changelog;
- задачи — GitHub Issues, а не Markdown-журнал.
