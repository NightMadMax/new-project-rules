---
type: guide
status: active
owner: project
last_verified: 2026-06-27
source_of_truth: repository
related:
  - "[[INDEX]]"
  - "[[README]]"
  - "[[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]]"
---

# Создание нового проекта

## Рекомендуемый способ: попросить агента

Сообщите название, путь, профиль и видимость GitHub-репозитория:

> Создай новый проект «Название» в папке `<путь>`, профиль `software`,
> приватный GitHub-репозиторий.

Если профиль не указан, используется `software`. Агент должен:

1. Создать папку проекта и применить bootstrap.
2. Сделать папку одновременно Obsidian vault и корнем git-репозитория.
3. Создать `AGENTS.md` и `CLAUDE.md` с единым источником правил.
4. Заполнить стартовые `README.md`, `PROJECT.md` и `INDEX.md`.
5. Добавить только подходящие проекту условные документы.
6. Инициализировать git, создать отдельный GitHub-репозиторий, выполнить
   первый commit и push.
7. Проверить bootstrap, git status и Obsidian wikilinks.

Для установки отсутствующего инструмента агент сначала объясняет причину и
запрашивает разрешение.

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

Папка нового проекта сама является vault. После bootstrap откройте именно её
через **Open folder as vault**.

Не размещайте проект внутри другого активно открытого vault. Удобнее держать
отдельные проекты рядом в общей родительской папке, например:

```text
Obsidian Projects/
├── Project A/   # отдельный vault и git repo
└── Project B/   # отдельный vault и git repo
```

## Заполнение стартовых документов

- [[PROJECT]] в новом vault: цель, scope, non-goals и критерии успеха.
- [[README]]: назначение и быстрый старт.
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
- `INDEX.md` содержит wikilinks на Markdown-заметки;
- папка открывается как отдельный Obsidian vault.

Следующий сценарий: [[docs/guides/SETUP_NEW_COMPUTER|подключение нового компьютера]].
