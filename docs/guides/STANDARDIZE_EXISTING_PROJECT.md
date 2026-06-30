---
type: guide
status: draft
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[docs/guides/ASSESS_EXISTING_PROJECT|ASSESS_EXISTING_PROJECT]]"
  - "[[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]]"
---

# Стандартизация существующего проекта

Этот guide описывает будущий workflow для уже существующего проекта, который
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
```

```powershell
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Example" -Strategy adopt-in-place -PlanAdopt
.\scripts\standardize-existing-project.ps1 -Root "C:\Projects\Example" -Strategy adopt-in-place -Apply -Fingerprint "<64-hex>" -Confirm
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
- обновление `INDEX.md` и `docs/README.md` только добавлением недостающих
  wikilinks;
- metadata adoption только через
  [[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]].

Требуют review и подтверждения:

- `README.md`
- `PROJECT.md`
- `AGENTS.md`
- существующие документы в `docs/`
- `.github/`, CI/CD, deployment configs, `.env*`

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

1. Создать новый проект через
   [[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]].
2. Перенести только согласованный набор файлов.
3. Довести docs и project files до стандарта уже в новом repo.
4. Прогнать validator.
5. Выполнить metadata adoption для нового проекта.
6. Отдельно перечислить, что осталось в legacy-проекте и что не переносилось.

## Ограничения первой версии

Первая версия standardization workflow пока ограничена:

- assessment автоматизирован отдельным read-only planner;
- `adopt-in-place` умеет только безопасные file creates и index updates;
- `README.md`, `PROJECT.md`, `AGENTS.md` и содержательные docs всё ещё требуют
  manual review;
- `re-bootstrap-from-existing` пока остаётся orchestration workflow без
  отдельного helper apply.
