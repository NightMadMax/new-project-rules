---
type: guide
status: active
owner: project
last_verified: 2026-07-05
source_of_truth: repository
related:
  - "[[README]]"
  - "[[INDEX]]"
  - "[[docs/guides/USE_THIS_PROJECT|USE_THIS_PROJECT]]"
  - "[[TOOLS]]"
  - "[[docs/quality/TESTING|TESTING]]"
  - "[[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]]"
  - "[[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/guides/SYNC_GLOBAL_AGENTS|SYNC_GLOBAL_AGENTS]]"
  - "[[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]]"
  - "[[docs/guides/STANDARDIZE_EXISTING_PROJECT|STANDARDIZE_EXISTING_PROJECT]]"
---

# Ручной запуск скриптов

Справочник-шпаргалка: как запустить каждый инструмент `scripts/*` вручную —
точная команда для macOS/Linux и Windows, ключевые флаги, когда это удобнее
агента и что безопасно. Глубокое поведение описано в per-workflow гайдах; здесь
только команды и ссылки, без дублирования.

## Когда вручную, а когда просить агента

- **Проси агента**, когда нужен целый workflow с проверками и заполнением
  документов (см. [[docs/guides/USE_THIS_PROJECT|USE_THIS_PROJECT]]).
- **Запускай вручную**, когда нужен точный контроль, повторяемость, запуск в CI
  или локальная проверка без агентского workflow.

## Предпосылки

- У каждого инструмента есть парные `.sh` (macOS/Linux) и `.ps1` (Windows).
- Python `3.9+` нужен для `validate-project`, `sync-global-agents`,
  `plan-migration`, `standardize-existing-project`, promotion candidates и
  `check-action-pins`.
  Обёртки `.sh`/`.ps1` сами находят `python3`/`python`.
- PowerShell `7+` нужен для `.ps1`. `gh` (авторизованный) нужен только для
  публикации GitHub-репозитория.
- Версии и установка инструментов — в [[TOOLS|TOOLS.md]] (не дублируется здесь).

## Соглашения безопасности

- Диагностические команды read-only: `check-environment`, `validate-project`,
  `project-doctor`, `sync-global-agents`, а также `plan`-режимы.
- Для планировщиков сначала используй `--plan`/`--report-only` и посмотри
  preview с fingerprint.
- Применяй изменения только явно: `--apply --fingerprint <value> --yes`
  (PowerShell: `-Apply -Fingerprint <value> -Confirm`) после проверенного плана.

## Справочник по семействам

### Создание проекта

Создаёт каркас нового проекта по профилю (`minimal`, `software`, `operated`,
`all`). Подробно: [[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]].

```sh
./scripts/bootstrap-new-project.sh "/path/to/New Project" "New Project" software
```

```powershell
.\scripts\bootstrap-new-project.ps1 -Destination "C:\Projects\New Project" -ProjectName "New Project" -Profile software
```

Правила для подкаталога (создаёт пару `AGENTS.md` + `CLAUDE.md`):

```sh
./scripts/add-agent-scope.sh services/api "Run API tests before changing handlers."
```

```powershell
.\scripts\add-agent-scope.ps1 -Directory services/api -Rule "Run API tests before changing handlers."
```

- Когда вручную: точечный старт проекта или scope без агентского workflow.

### Настройка компьютера и глобальные правила

Один раз на компьютер настраивает `~/.claude/CLAUDE.md` с импортом
`@~/.codex/AGENTS.md`; идемпотентно, существующие инструкции не перезаписывает.
Подробно: [[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]].

```sh
./scripts/setup-global-agents.sh
./scripts/check-environment.sh both     # codex | claude | both
```

```powershell
.\scripts\setup-global-agents.ps1
.\scripts\check-environment.ps1 -AgentMode both
```

- Когда вручную: подключение нового Mac/Windows, проверка обязательной базы
  инструментов. `check-environment` read-only.

### Best Practices consumer manifest

Создаёт или обновляет только preferences в schema 2 manifest; существующие
practice outcomes сохраняются. Schema 1 нужно сначала мигрировать отдельным
workflow Best Practices.

```sh
python3 scripts/best_practices_manifest.py --project "/path/to/Project" --set-global optout
python3 scripts/best_practices_manifest.py --project "/path/to/Project" --set-section python ask
```

```powershell
python .\scripts\best_practices_manifest.py --project "C:\Projects\Project" --set-global optout
```

- Когда вручную: зафиксировать global/section opt-in или opt-out без изменения
  outcomes. Результат нужно проверить и закоммитить в consumer repository.

### Валидация и диагностика

Read-only проверка структуры проекта или набора правил и общая диагностика
среды. Подробно: [[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE]].

```sh
./scripts/validate-project.sh --root . --kind rules
./scripts/validate-project.sh --root "/path/to/Project" --kind project --profile software
./scripts/project-doctor.sh --root . --agent-mode both --profile auto --report-only
```

```powershell
.\scripts\validate-project.ps1 -Root . -Kind rules
.\scripts\project-doctor.ps1 -Root . -AgentMode both -Profile auto -ReportOnly
```

- Ключевые флаги: `--kind auto|rules|project`, `--profile auto|minimal|software|operated|all`,
  `--doctor`, `--report-only`.
- Когда вручную: быстрая структурная проверка, локально или в CI.

### Компрессия проекта

Уровень-1 уборка накопившегося «мусора»: отчёт по умолчанию, `--apply` делает
только обратимое. Нацеливается на любой стандартизированный проект через
`--root`. Подробно: [[docs/guides/COMPRESS_PROJECT|COMPRESS_PROJECT]].

```sh
./scripts/compress-project.sh --root .
./scripts/compress-project.sh --root "/path/to/Project" --apply
```

```powershell
.\scripts\compress-project.ps1 -Root .
.\scripts\compress-project.ps1 -Root "C:\path\to\Project" -Apply
```

- Ключевые флаги: `--apply`, `--today`, `--changelog-max-kb`, `--changelog-keep`,
  `--fixed-max-age-days`, `--stale-days`.
- Когда вручную: периодическая уборка или подготовка к релизу. Консолидацию docs
  и память агентов ведёт скилл `compress-project`, а не скрипт.

### Глобальная политика агентов

Read-only проверка и secret-safe diff переносимых глобальных инструкций против
`~/.codex/AGENTS.md`. Подробно:
[[docs/guides/SYNC_GLOBAL_AGENTS|SYNC_GLOBAL_AGENTS]].

```sh
./scripts/sync-global-agents.sh --check
./scripts/sync-global-agents.sh --diff --report-only
```

```powershell
.\scripts\sync-global-agents.ps1 -Check
.\scripts\sync-global-agents.ps1 -Diff -ReportOnly
```

- Когда вручную: проверить drift глобальных правил; diff не показывает
  содержимое приватных инструкций.

### Миграции project / global metadata

Fingerprint-защищённый планировщик и исполнитель миграций
`.project-standard.json` и managed global policy. Подробно:
[[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]].

```sh
./scripts/plan-migration.sh --plan --target project --root "/path/to/Project" --profile software --report-only
./scripts/plan-migration.sh --apply --target project --root "/path/to/Project" --fingerprint <value> --yes
```

```powershell
.\scripts\plan-migration.ps1 -Plan -Target project -Root "C:\Projects\Project" -Profile software -ReportOnly
.\scripts\plan-migration.ps1 -Apply -Target project -Root "C:\Projects\Project" -Fingerprint <value> -Confirm
```

- Ключевые флаги: `--target project|global`, `--plan`/`--apply`,
  `--fingerprint`, `--yes`.
- Когда вручную: переход на новую схему metadata; всегда сначала `--plan`.

### Стандартизация существующего проекта

По умолчанию read-only decision report; отдельными режимами — reviewable
adopt-in-place или re-bootstrap план. Подробно:
[[docs/guides/STANDARDIZE_EXISTING_PROJECT|STANDARDIZE_EXISTING_PROJECT]].

```sh
./scripts/standardize-existing-project.sh --root "/path/to/Legacy"
./scripts/standardize-existing-project.sh --root "/path/to/Legacy" --plan-adopt --profile software
```

```powershell
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Legacy"
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Legacy" -PlanAdopt -Profile software
```

- Ключевые флаги: `--strategy auto|adopt-in-place|re-bootstrap-from-existing`,
  `--plan-adopt`, `--plan-rebootstrap`, `--apply`, `--fingerprint`, `--yes`.
- Когда вручную: анализ legacy-проекта без изменений; apply — только по плану.

### Supply-chain (для мейнтейнеров набора правил)

Запрещает mutable-ссылки на внешние GitHub Actions (только full commit SHA).

```sh
python3 scripts/check-action-pins.py --root .
```

- Когда вручную: проверка pin-политики Actions перед изменением workflow.

### Promotion candidates

Создаёт отдельный candidate file с collision-resistant ID и проверяет всю
очередь:

```sh
python3 scripts/promotion_candidates.py create --help
python3 scripts/promotion_candidates.py validate
```

- Когда вручную: добавить нормализованный lesson без редактирования общей
  таблицы или проверить schema/дубли ID перед review.

### Тесты

Команды и матрица регрессионных тестов не дублируются здесь — см.
[[docs/quality/TESTING|TESTING.md]].

## Частые сценарии

| Задача | Команда (macOS/Linux) |
|---|---|
| Проверить этот репозиторий правил | `./scripts/validate-project.sh --root . --kind rules` |
| Проверить чужой проект как `software` | `./scripts/validate-project.sh --root <path> --kind project --profile software` |
| Диагностика среды и проекта | `./scripts/project-doctor.sh --root . --report-only` |
| Отчёт о компрессии проекта | `./scripts/compress-project.sh --root .` |
| Проверить drift глобальных правил | `./scripts/sync-global-agents.sh --diff --report-only` |
| План миграции без изменений | `./scripts/plan-migration.sh --plan --target project --root <path> --report-only` |
| Оценить legacy-проект | `./scripts/standardize-existing-project.sh --root <path>` |
