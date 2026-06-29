---
type: guide
status: active
owner: project
last_verified: 2026-06-29
source_of_truth: repository
related:
  - "[[docs/architecture/PROJECT_STANDARD_SCHEMA]]"
  - "[[docs/guides/SYNC_GLOBAL_AGENTS]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN]]"
---

# Планирование миграций

Planner строит reviewable план перехода legacy state (`schema=0`) к текущему
стандарту. На этом этапе доступен только `--plan`: он не создаёт metadata, не
добавляет markers и не делает backup.

## Legacy project

macOS/Linux:

```sh
./scripts/plan-migration.sh --plan --target project --root "/path/to/project"
```

Windows PowerShell:

```powershell
.\scripts\plan-migration.ps1 -Plan -Target project -Root "C:\Projects\Example"
```

Planner:

1. определяет профиль только по точному составу managed artifacts или принимает
   явно проверенный `--profile` / `-Profile`;
2. требует отдельный чистый Git repository проекта;
3. требует чистый committed source `new-project-rules`;
4. показывает точное содержимое будущего `.project-standard.json`;
5. оставляет `created_at=null`, потому что дату создания legacy-проекта нельзя
   достоверно восстановить.

Статус `blocked` означает, что план построен, но apply был бы небезопасен:
например, профиль неоднозначен, tree dirty или metadata уже повреждена.

## Global policy

```sh
./scripts/plan-migration.sh --plan --target global
```

```powershell
.\scripts\plan-migration.ps1 -Plan -Target global
```

Для `legacy_exact` план предлагает обернуть совпадающий текст markers и перед
будущим apply создать timestamped backup. Содержимое active policy не печатается:
используются только состояние, диапазоны, число строк и SHA-256. Конфликт,
повреждённые markers или unsupported schema блокируют adoption.

## Exit codes

- `0` — план готов или migration не требуется;
- `1` — план заблокирован precondition;
- `2` — некорректная команда или migration contract;
- `--report-only` / `-ReportOnly` — всегда `0` после вывода отчёта.

Каждый отчёт завершается `No files were changed.`. Apply появится только после
отдельной реализации backup, clean-tree recheck, atomic write и idempotence.
