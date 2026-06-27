---
type: research
status: accepted
owner: project
last_verified: 2026-06-27
source_of_truth: repository
---

# Модель артефактов проекта

| Условие | Артефакт |
|---|---|
| Любой проект | `README.md`, `AGENTS.md`, `INDEX.md`, `PROJECT.md` |
| Есть релизы | `CHANGELOG.md` |
| Есть значимые технические решения | `docs/architecture/decisions/` |
| Есть исполняемый код | `docs/architecture/`, `docs/quality/TESTING.md` |
| Есть внешние операции | `ACTIONS.md` |
| Есть production/устройства | `docs/operations/` |
| Есть API | `docs/api/INTERFACES.md` и API-spec |
| Есть постоянные данные | `docs/data/` |
| Есть чувствительные активы | `SECURITY.md`, `docs/security/` |
| Есть внешние сервисы | `INTEGRATIONS.md` |
| Есть необычные инструменты | `TOOLS.md` |

Разделение строится не по формату, а по жизненному циклу информации:

- текущее состояние системы — архитектура и интерфейсы;
- причины выбора — ADR;
- проверяемые гипотезы — исследования;
- воспроизводимые действия — runbook;
- произошедшие сбои — postmortem;
- пользовательские изменения — changelog;
- задачи — GitHub Issues, а не Markdown-журнал.
