---
type: guide
status: active
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[docs/architecture/PROJECT_STANDARD_SCHEMA]]"
  - "[[docs/guides/SYNC_GLOBAL_AGENTS]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN]]"
---

# Планирование миграций

Migration engine строит reviewable план перехода legacy state (`schema=0`) к
текущему стандарту. `--plan` ничего не меняет и выдаёт fingerprint; `--apply`
принимает только этот fingerprint, повторно проверяет state и требует явное
подтверждение.

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

После review скопируйте fingerprint из того же плана:

```sh
./scripts/plan-migration.sh --apply --target project \
  --root "/path/to/project" --profile software \
  --fingerprint "<64-hex>" --yes
```

```powershell
.\scripts\plan-migration.ps1 -Apply -Target project `
  -Root "C:\Projects\Example" -Profile software `
  -Fingerprint "<64-hex>" -Confirm
```

Apply создаёт только `.project-standard.json` через temporary file и atomic
replace. Файл остаётся unstaged: проверьте `git diff -- .project-standard.json`
и закоммитьте его отдельно. Повторный запуск возвращает `up_to_date`. Existing
metadata symlink блокируется и автоматически не заменяется.

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

Подтверждённый apply:

```sh
./scripts/plan-migration.sh --apply --target global \
  --fingerprint "<64-hex>" --yes
```

```powershell
.\scripts\plan-migration.ps1 -Apply -Target global `
  -Fingerprint "<64-hex>" -Confirm
```

Перед atomic replace создаётся побайтовый backup рядом с active file:
`AGENTS.md.bak.<UTC timestamp>`. Если active state изменился после plan или во
время backup, apply останавливается. Rollback — заменить active file этим backup
и повторно запустить check/plan. Existing `AGENTS.md` symlink автоматически не
заменяется: plan будет `blocked`, пока владение ссылкой не разобрано вручную.

## Exit codes

- `0` — план готов, apply verified или migration не требуется;
- `1` — план заблокирован precondition;
- `2` — некорректная команда или migration contract;
- `--report-only` / `-ReportOnly` — всегда `0` после вывода отчёта.

Read-only отчёт завершается `No files were changed.`. `--report-only` запрещён
с `--apply`, а fingerprint/confirmation нельзя передавать режиму `--plan`.
