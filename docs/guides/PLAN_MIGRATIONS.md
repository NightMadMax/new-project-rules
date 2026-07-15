---
type: guide
status: active
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/architecture/PROJECT_STANDARD_SCHEMA]]"
  - "[[docs/guides/SYNC_GLOBAL_AGENTS]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN]]"
---

# Планирование миграций

Migration engine строит reviewable план по единственной последовательной цепочке
от текущей schema (включая legacy `0`) к стандарту. Пропущенный или
неоднозначный переход делает contract невалидным. `--plan` ничего не меняет и выдаёт fingerprint; `--apply`
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

Для существующей metadata schema `1` план `1 → 2` сохраняет профиль и даты,
обновляет source commit и дописывает ровно следующий migration ID. История
`applied_migrations` обязана точно совпадать с детерминированным путём; заранее
заявленный или пропущенный ID блокирует apply.

## Project AGENTS baseline

```sh
./scripts/plan-migration.sh --plan --target project-agents --root "/path/to/project"
```

```powershell
.\scripts\plan-migration.ps1 -Plan -Target project-agents -Root "C:\Projects\Example"
```

Target `project-agents` владеет managed-блоком внутри `AGENTS.md` проекта.
Локальные секции вне маркеров сохраняются без изменений. `legacy_exact`,
`managed_drift` и `managed_upgrade` обновляются с timestamped backup.

`unmanaged_conflict` (файл без маркеров, не совпадающий с baseline) блокируется
намеренно. Под это состояние попадают два противоположных случая, и планировщик
не может их различить:

- файл содержит только локальные правила — baseline нужно дописать снизу;
- файл содержит устаревшую копию baseline без маркеров — дописывание
  продублирует правила.

Решение принимает человек. Прочитайте файл и, если его содержимое локальное,
повторите с явным review-флагом:

```sh
./scripts/plan-migration.sh --plan --target project-agents \
  --root "/path/to/project" --accept-unmanaged-as-local
```

```powershell
.\scripts\plan-migration.ps1 -Plan -Target project-agents `
  -Root "C:\Projects\Example" -AcceptUnmanagedAsLocal
```

План тогда дописывает managed block ниже существующего текста, сохраняя его
построчно, и требует timestamped backup. Флаг допустим только с
`--target project-agents`; с другими targets он возвращает `2`. Fingerprint и
подтверждение остаются обязательными.

## Global policy

```sh
./scripts/plan-migration.sh --plan --target global
```

```powershell
.\scripts\plan-migration.ps1 -Plan -Target global
```

Для `legacy_exact` план предлагает обернуть совпадающий текст markers и перед
будущим apply создать timestamped backup. Для `unmanaged_conflict` (файл уже
содержит собственные правила без markers) план дописывает managed block **ниже**
существующего текста, сохраняя его без изменений, и тоже требует timestamped
backup. Содержимое active policy не печатается: используются только состояние,
диапазоны, число строк и SHA-256. `managed_upgrade` и `managed_drift`
обновляются с backup и сохранением текста вне markers. Повреждённые markers и
future/unsupported schema блокируют apply.

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
