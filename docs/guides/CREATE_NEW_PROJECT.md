---
type: guide
status: active
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[INDEX]]"
  - "[[README]]"
  - "[[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]]"
---

# Создание нового проекта

## Рекомендуемый способ: попросить агента

Используйте `$create-new-project` в Codex или `/create-new-project` в Claude
Code либо сформулируйте запрос обычным языком.

Сообщите название, путь, профиль и видимость GitHub-репозитория:

> Создай новый проект «Название» в папке `<путь>`, профиль `software`,
> приватный GitHub-репозиторий.

Если профиль не указан, используется `software`. Агент должен:

1. Создать папку проекта и применить bootstrap.
2. Создать папку внутри общего Obsidian vault и сделать её корнем отдельного
   git-репозитория.
3. Создать `AGENTS.md` и `CLAUDE.md` с единым источником правил.
4. Зафиксировать в `AGENTS.md`, что все ответы, исследования, ревью, планы и
   отчёты пользователю даются на русском языке, если пользователь прямо не
   запросил другой язык.
5. Заполнить стартовые `README.md`, `PROJECT.md` и `INDEX.md`.
6. Добавить только подходящие проекту условные документы.
7. Инициализировать git, создать отдельный GitHub-репозиторий, выполнить
   первый commit и push.
8. Проверить bootstrap, git status и Obsidian wikilinks.

Для установки отсутствующего инструмента агент сначала объясняет причину и
запрашивает разрешение.

Готовые формулировки:

> Создай новый проект «Название» в папке `<путь>` внутри общего Obsidian vault,
> профиль `software`, приватный GitHub-репозиторий.

> Создай новый local-only проект «Название» в папке `<путь>`, профиль
> `minimal`, без GitHub-репозитория.

Если проект создаётся уже на новом компьютере после первичной настройки, сначала
выполните [[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]], а затем
попросите агента создать проект этим workflow.

## Выбор профиля

| Профиль | Когда использовать |
|---|---|
| `minimal` | Документация, исследование или небольшой проект без кода |
| `software` | Обычный программный проект; профиль по умолчанию |
| `operated` | Есть серверы, устройства, деплой или ручные операции |
| `all` | Нужны API, данные, эксплуатация и security-документация |

## Создание вручную на macOS/Linux

Из корня проекта [[README|«Правила для нового проекта»]]:

```sh
./scripts/bootstrap-new-project.sh \
  "/path/to/New Project" \
  "New Project" \
  software
```

## Создание вручную в Windows PowerShell

```powershell
.\scripts\bootstrap-new-project.ps1 `
  -Destination "C:\Projects\New Project" `
  -ProjectName "New Project" `
  -Profile software
```

Bootstrap принимает отсутствующую или пустую папку. Непустая папка считается
конфликтом и не изменяется.

## Obsidian

Папка нового проекта не является отдельным vault. Создавайте её внутри общей
папки, уже открытой в Obsidian через **Open folder as vault**, например:

```text
AiProject/       # общий Obsidian vault
├── Project A/   # отдельный git repo
└── Project B/   # отдельный git repo
```

## Заполнение стартовых документов

- [[PROJECT]] в новой папке проекта: цель, scope, non-goals и критерии успеха.
- [[README]]: назначение и быстрый старт. Секция «Источник» называет стандарт
  и отсылает к `.project-standard.json`; не вписывайте commit вручную — он
  попадёт в метаданные на шаге плана миграции.
- [[AGENTS]] → `Commands`: только реально проверенные команды.
- [[INDEX]]: только фактически существующие заметки и файлы.

Если проект уже содержит код, агент должен исследовать manifests и заполнить
команды install, build, test, lint и run. Не оставляйте фиктивные команды.

## Создание GitHub-репозитория вручную

```sh
cd "/path/to/New Project"
git add .
git commit -m "Initialize project"
gh repo create NightMadMax/new-project-repo \
  --private \
  --source=. \
  --remote=origin \
  --push
```

Для публичного проекта замените `--private` на `--public`. Название GitHub-
репозитория лучше записывать латиницей без пробелов.

## Проверка результата

```sh
git status --short
git remote -v
```

Ожидаемый результат:

- рабочее дерево чистое;
- ветка `main` отслеживает `origin/main`;
- `CLAUDE.md` содержит только `@AGENTS.md`;
- `AGENTS.md` требует отвечать пользователю на русском языке;
- `INDEX.md` содержит wikilinks на Markdown-заметки;
- папка проекта видна внутри общего Obsidian vault и не содержит `.obsidian`.

Когда документы заполнены и Git tree чистый, постройте reviewable metadata plan:

```sh
./scripts/plan-migration.sh --plan --target project \
  --root "/path/to/New Project" --profile software --report-only
```

```powershell
.\scripts\plan-migration.ps1 -Plan -Target project `
  -Root "C:\Projects\New Project" -Profile software -ReportOnly
```

Скопируйте fingerprint только после review и примените план:

```sh
./scripts/plan-migration.sh --apply --target project \
  --root "/path/to/New Project" --profile software \
  --fingerprint "<64-hex>" --yes
```

```powershell
.\scripts\plan-migration.ps1 -Apply -Target project `
  -Root "C:\Projects\New Project" -Profile software `
  -Fingerprint "<64-hex>" -Confirm
```

До plan дерево должно быть чистым; после apply проверьте и отдельно закоммитьте
только `.project-standard.json`. Подробности: [[docs/guides/PLAN_MIGRATIONS|планирование миграций]].

Следующий сценарий: [[docs/guides/SETUP_NEW_COMPUTER|подключение нового компьютера]].
