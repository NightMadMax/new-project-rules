---
type: guide
status: active
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/guides/ASSESS_EXISTING_PROJECT|ASSESS_EXISTING_PROJECT]]"
  - "[[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]]"
---

# Стандартизация существующего проекта

Этот guide описывает текущий workflow для уже существующего проекта, который
нужно привести к стандарту `new-project-rules`. В отличие от
[[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]], здесь bootstrap не
запускается вслепую поверх существующей папки.

## Цель

Для legacy-проекта нужно сначала выбрать безопасную стратегию:

1. `adopt-in-place` — изменить существующий проект в той же папке и том же
   репозитории.
2. `re-bootstrap-from-existing` — создать новый проект по правилам и перенести
   в него согласованные артефакты из существующего проекта.

Workflow должен сначала опираться на отдельный assessment через
[[docs/guides/ASSESS_EXISTING_PROJECT|ASSESS_EXISTING_PROJECT]], и только после
этого менять файлы.

Workflow предназначен только для consumer projects. Канонический
`new-project-rules` определяется как `target_kind=rules-repository`, получает
`status=not_applicable` и не допускается к `adopt-in-place`,
`re-bootstrap-from-existing`, plan или apply. Для самого стандарта используются
rules validator и архитектурный audit.

## Рекомендуемый способ: попросить агента

Используйте `$standardize-existing-project` в Codex или
`/standardize-existing-project` в Claude Code.

Примеры запросов:

> Приведи существующий проект `<path>` к стандарту `new-project-rules`, ничего
> не удаляй без согласования.

> Посмотри проект `<path>` и скажи, лучше его доработать на месте или
> пересоздать по шаблону.

> Создай новый проект по правилам на основе существующего `<path>` и перенеси
> только код, тесты и безопасные конфиги.

Assessment по-прежнему read-only:

```sh
./scripts/standardize-existing-project.sh --root "/path/to/project"
```

```powershell
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Example"
```

Для machine-readable отчёта:

```sh
python3 scripts/standardize_existing_project.py --root "/path/to/project" --json
```

Для безопасного `adopt-in-place` plan/apply:

```sh
./scripts/standardize-existing-project.sh --root "/path/to/project" --strategy adopt-in-place --plan-adopt
./scripts/standardize-existing-project.sh --root "/path/to/project" --strategy adopt-in-place --apply --fingerprint "<64-hex>" --yes
./scripts/standardize-existing-project.sh --root "/path/to/project" --strategy re-bootstrap-from-existing --plan-rebootstrap --destination "/path/to/New Project" --project-name "New Project"
./scripts/standardize-existing-project.sh --root "/path/to/project" --strategy re-bootstrap-from-existing --apply --destination "/path/to/New Project" --project-name "New Project" --fingerprint "<64-hex>" --yes
```

```powershell
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Example" -Strategy adopt-in-place -PlanAdopt
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Example" -Strategy adopt-in-place -Apply -Fingerprint "<64-hex>" -Confirm
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Example" -Strategy re-bootstrap-from-existing -PlanRebootstrap -Destination "C:\Projects\New Project" -ProjectName "New Project"
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Example" -Strategy re-bootstrap-from-existing -Apply -Destination "C:\Projects\New Project" -ProjectName "New Project" -Fingerprint "<64-hex>" -Confirm
```

## Что должен сделать агент

### 1. Assess

Агент сначала обязан выполнить отдельный assessment workflow:

1. Запустить [[docs/guides/ASSESS_EXISTING_PROJECT|ASSESS_EXISTING_PROJECT]].
2. Получить decision report без изменения файлов.
3. Только после этого переходить к сравнению и выбору стратегии.

### 2. Сравнить стратегии

Агент обязан показать оба варианта, если оба технически возможны:

#### `adopt-in-place`

Подходит, когда:

- структура проекта уже близка к одному из профилей;
- существующий repo нужно сохранить как основной;
- конфликтов по `README.md`, `PROJECT.md`, `AGENTS.md`, `INDEX.md` немного;
- документацию можно довести incremental-правками.

План должен перечислить:

- какие managed files можно безопасно создать;
- какие файлы можно только дополнить;
- какие документы требуют ручного merge-review;
- какие блокеры мешают apply.

#### `re-bootstrap-from-existing`

Подходит, когда:

- legacy-структура слишком хаотична;
- безопаснее собрать clean project по правилам рядом со старым;
- нужно сохранить старый repo как reference или архив;
- перенос кода и docs проще, чем правка текущего дерева на месте.

План должен перечислить:

- куда будет создан новый проект;
- какой профиль предлагается;
- какие папки и файлы предлагается перенести автоматически;
- какие файлы запрещено переносить без review.

### 3. Попросить выбрать стратегию

Перед любыми изменениями агент должен явно запросить выбор:

- `adopt-in-place`
- `re-bootstrap-from-existing`

Если одна стратегия небезопасна, агент должен объяснить blocker и рекомендовать
другую.

## Безопасные автоматические действия

### Для `adopt-in-place`

Можно автоматизировать без отдельного ручного merge:

- создание отсутствующего `CLAUDE.md` со строкой `@AGENTS.md`;
- создание `.gitignore`, `.gitattributes`, `.editorconfig`, если файлов нет;
- создание `docs/README.md`, если уже существует `docs/`, но нет индекса;
- создание `docs/quality/STANDARD_ADOPTION.json`, если журнала нет: он
  начинается с `adopted_at` из `.project-standard.json`, а без metadata — с
  сегодняшней даты, потому что дату создания legacy-проекта восстановить нельзя;
- обновление `INDEX.md` и `docs/README.md` только добавлением недостающих
  wikilinks;
- metadata adoption и managed baseline в `AGENTS.md` — только через
  [[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]].

Требуют review и подтверждения:

- `README.md`
- `PROJECT.md`
- существующие документы в `docs/`
- `.github/`, CI/CD, deployment configs, `.env*`

`AGENTS.md` руками не правится. Его managed-блок вносит
`plan-migration --target project-agents`; для `unmanaged_conflict` нужен явный
review-флаг `--accept-unmanaged-as-local`, потому что под это состояние
попадают и чисто локальный файл, и устаревшая копия baseline.

### Для `re-bootstrap-from-existing`

Можно переносить по умолчанию:

- `src/`, `app/`, `lib/`, `tests/`
- manifests
- безопасные project configs без credentials
- выбранные Markdown-документы после review

Нельзя переносить автоматически без отдельного решения:

- secrets и `.env*`
- machine-specific configs
- старые agent instructions без review
- deployment credentials
- сомнительные CI/workflow файлы

## Ожидаемый вывод decision report

Assessment должен возвращать не свободный текст, а понятную структуру решения:

- `target_kind`
- `recommended_strategy`
- `candidate_profile`
- `safe_to_adopt_in_place`
- `safe_to_rebootstrap`
- `blocking_issues`
- `files_to_create`
- `files_to_merge`
- `files_to_review_manually`
- `proposed_transfer_set`

## Поведение после выбора

### Если выбран `adopt-in-place`

1. Построить reviewable `--plan-adopt`.
2. Создать только отсутствующие безопасные managed files:
   `CLAUDE.md`, `.gitignore`, `.gitattributes`, `.editorconfig`,
   `docs/README.md`.
3. Аккуратно обновить `INDEX.md` и `docs/README.md` только добавлением
   отсутствующих wikilinks.
4. Применять изменения только по подтверждённому fingerprint и `--yes`.
5. Прогнать validator.
6. Построить `plan-migration --target project`.
7. Применить metadata adoption только по подтверждённому fingerprint.
8. Сообщить, что ещё осталось вручную.

### Если выбран `re-bootstrap-from-existing`

1. Построить reviewable `--plan-rebootstrap` с `--destination` и
   `--project-name`.
2. Создать новый проект через existing bootstrap profile.
3. Перенести только safe transfer set: код, тесты и manifests.
4. Не переносить docs, agent files, secrets и deployment artifacts автоматически.
5. Прогнать validator для нового проекта.
6. Проверить, что bootstrap создал актуальную `.project-standard.json`; metadata
   migration нужна только для старого bootstrap output.
7. Отдельно перечислить, что осталось в legacy-проекте и что не переносилось.

## Ограничения первой версии

Первая версия standardization workflow пока ограничена:

- assessment автоматизирован отдельным read-only planner;
- `adopt-in-place` умеет только безопасные file creates и index updates;
- `README.md`, `PROJECT.md` и содержательные docs всё ещё требуют manual review;
- `AGENTS.md` не требует ручной правки: baseline вносится миграцией
  `project-agents`, а review сводится к решению, локальный ли текст вне
  маркеров;
- `re-bootstrap-from-existing` уже умеет bootstrap нового проекта и safe-set
  apply, но содержательные docs, agent files и deployment-конфиги всё ещё
  требуют отдельного review.
- rules repository и его полные копии исключены из consumer-project workflow;
  один случайный файл `STANDARD_VERSION` в обычном проекте это исключение не
  активирует.
