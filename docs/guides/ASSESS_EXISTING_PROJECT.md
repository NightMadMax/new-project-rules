---
type: guide
status: draft
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[docs/guides/STANDARDIZE_EXISTING_PROJECT|STANDARDIZE_EXISTING_PROJECT]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]]"
---

# Оценка существующего проекта

Этот guide описывает read-only workflow для уже существующего проекта. Его цель
— не менять файлы, а ответить, можно ли безопасно приводить проект к стандарту
на месте или лучше создавать новый проект по правилам на его основе.

## Рекомендуемый способ: попросить агента

Используйте `$assess-existing-project` в Codex или `/assess-existing-project`
в Claude Code.

Примеры запросов:

> Оцени существующий проект `<path>` относительно `new-project-rules` и скажи,
> можно ли безопасно привести его к стандарту на месте.

> Посмотри проект `<path>` и подготовь read-only decision report: что в нём не
> так, какой профиль ближе и стоит ли делать `adopt-in-place`.

## Что делает assessment

Assessment:

1. ничего не изменяет в проекте;
2. проверяет repository state, managed files, core docs и Obsidian placement;
3. запускает validator/doctor там, где это безопасно и уместно;
4. определяет `candidate_profile` или помечает его как неоднозначный;
5. строит decision report для будущего workflow стандартизации.

## Команды

macOS/Linux:

```sh
./scripts/standardize-existing-project.sh --root "/path/to/project"
```

Windows PowerShell:

```powershell
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Example"
```

Machine-readable JSON:

```sh
python3 scripts/standardize_existing_project.py --root "/path/to/project" --json
```

## Что должно быть в отчёте

- `recommended_strategy`
- `candidate_profile`
- `safe_to_adopt_in_place`
- `safe_to_rebootstrap`
- `blocking_issues`
- `files_to_create`
- `files_to_merge`
- `files_to_review_manually`
- `proposed_transfer_set`

## Что assessment не делает

- не запускает bootstrap поверх существующего проекта;
- не создаёт новые managed files;
- не обновляет `INDEX.md` и `docs/README.md`;
- не пишет `.project-standard.json`;
- не переносит код в новый проект.

Следующий шаг после assessment:
[[docs/guides/STANDARDIZE_EXISTING_PROJECT|STANDARDIZE_EXISTING_PROJECT]].
