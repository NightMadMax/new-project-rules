---
name: assess-existing-project
description: Выполняет read-only оценку существующего проекта относительно стандарта new-project-rules и строит decision report: какой профиль ближе, можно ли делать adoption in place и когда безопаснее создать новый стандартизированный проект на его основе. Использовать, когда пользователь хочет только проверить legacy-проект, понять разрыв до стандарта или получить рекомендацию без изменения файлов.
---

# Оценка существующего проекта

Этот skill отвечает только за assessment. Он не меняет файлы и не запускает
bootstrap/adoption.

## Найти источник правил

1. Найти корень `new-project-rules`: каталог должен содержать `AGENTS.md`,
   `docs/guides/`, `scripts/` и `config/`.
2. Полностью прочитать корневой `AGENTS.md`,
   `docs/guides/ASSESS_EXISTING_PROJECT.md`,
   `docs/guides/VALIDATE_AND_DIAGNOSE.md` и
   `docs/guides/PLAN_MIGRATIONS.md`. Эти файлы имеют приоритет над skill.

## Выполнить assessment

1. Получить путь к существующему проекту.
2. Ничего не изменять до конца workflow.
3. Проверить repository state, core docs, `CLAUDE.md`, `docs/README.md`,
   nested `.obsidian`, conflicts и dirty tree.
4. При наличии runtime выполнить read-only checks:
   - macOS/Linux: `./scripts/validate-project.sh ...`,
     `./scripts/project-doctor.sh ...`,
     `./scripts/standardize-existing-project.sh --root <target>`;
   - Windows: `.\scripts\validate-project.ps1 ...`,
     `.\scripts\project-doctor.ps1 ...`,
     `.\scripts\standardize-existing-project.ps1 -Root <target>`.
5. При необходимости machine-readable output вызвать
   `python scripts/standardize_existing_project.py --root <target> --json`.
6. Вернуть decision report с полями:
   - `recommended_strategy`
   - `candidate_profile`
   - `safe_to_adopt_in_place`
   - `safe_to_rebootstrap`
   - `blocking_issues`
   - `files_to_create`
   - `files_to_merge`
   - `files_to_review_manually`
   - `proposed_transfer_set`

## Что сообщить пользователю

1. Какой профиль выглядит ближайшим и почему.
2. Безопасен ли `adopt-in-place`.
3. Когда лучше `re-bootstrap-from-existing`.
4. Какие файлы можно будет создать автоматически, а какие требуют manual review.
5. Какие блокеры нужно снять до стандартизации.

## Ограничения

1. Не запускать `create-new-project` и не создавать новый repo.
2. Не изменять текущий проект даже если strategy выглядит очевидной.
3. Если пользователь хочет переходить к изменениям, передать результат workflow
   `standardize-existing-project`.
