---
name: create-new-project
description: Создаёт новый проект внутри общего Obsidian vault по шаблонам new-project-rules, инициализирует отдельный git-репозиторий и публикует отдельный GitHub repository. Использовать, когда пользователь просит создать, начать, bootstrap или опубликовать новый проект; не использовать для подключения существующего repository.
---

# Создание нового проекта

Создать готовый к работе проект из канонического bootstrap, без пустых
артефактов, секретов и второго Obsidian vault.

## Найти источник правил

1. Найти корень `new-project-rules`: каталог должен содержать `AGENTS.md`,
   `templates/new-project/`, `scripts/` и `docs/guides/`.
2. Сначала искать корень над каталогом этого skill; не зависеть от текущего
   рабочего каталога.
3. Полностью прочитать корневой `AGENTS.md` и
   `docs/guides/CREATE_NEW_PROJECT.md`. Они имеют приоритет над этим workflow.

## Определить параметры

1. Получить название проекта. Если путь не указан, создать проект рядом с
   `new-project-rules` внутри общего родительского vault.
2. Если профиль не указан, использовать `software`. Допустимые профили:
   `minimal`, `software`, `operated`, `all`.
3. Если GitHub visibility не указана, использовать `private`. Создать отдельный
   repository, если пользователь явно не запросил local-only или monorepo.
4. Получить или безопасно вывести GitHub slug: lowercase Latin letters, digits
   и hyphens. Не угадывать неоднозначную транслитерацию без подтверждения.

## Создать проект

1. Убедиться, что destination отсутствует или пуст. Не запускать bootstrap над
   существующим проектом и не удалять его содержимое.
2. Проверить обязательные инструменты и `gh auth status`. Перед установкой
   отсутствующего инструмента объяснить необходимость и получить разрешение.
3. Запустить из корня правил:
   - macOS/Linux: `./scripts/bootstrap-new-project.sh <destination> <name> <profile>`;
   - Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap-new-project.ps1 -Destination <destination> -ProjectName <name> -Profile <profile>`.
4. Заполнить `PROJECT.md`, `README.md` и `INDEX.md` фактическими данными задачи.
   Удалить неприменимые секции и не создавать условные документы без текущей
   необходимости. Секцию «Источник» в `README.md` оставить: она называет
   стандарт и отсылает к `.project-standard.json`; commit туда вручную не
   вписывать — он попадёт в метаданные на шаге 8–9.
5. Проверить `AGENTS.md`, `CLAUDE.md=@AGENTS.md`, wikilinks, отсутствие
   `.obsidian`, абсолютных machine-specific paths и секретов.
6. Если доступен Python 3.9+, запустить read-only validator из корня правил:
   - macOS/Linux: `./scripts/validate-project.sh --root <destination> --kind project --profile <profile>`;
   - Windows: `.\scripts\validate-project.ps1 -Root <destination> -Kind project -Profile <profile>`.
   При отсутствии Python выполнить существующие ручные проверки и явно сообщить,
   что расширенная валидация пропущена; не устанавливать Python без разрешения.
7. Если bootstrap создал начальный commit до заполнения документов, сделать
   отдельный осмысленный commit с завершённой конфигурацией. Перед migration
   plan рабочее дерево обязано быть чистым.
8. Построить plan adoption metadata с явным выбранным profile:
   - macOS/Linux: `./scripts/plan-migration.sh --plan --target project --root <destination> --profile <profile> --report-only`;
   - Windows: `.\scripts\plan-migration.ps1 -Plan -Target project -Root <destination> -Profile <profile> -ReportOnly`.
   Проверить preview и сохранить выданный fingerprint. Если plan `ready`,
   применить его через `--apply --fingerprint <value> --yes` или PowerShell
   `-Apply -Fingerprint <value> -Confirm`; не создавать metadata вручную.
9. Проверить, что apply добавил только `.project-standard.json`, повторный plan
   возвращает `up_to_date`, затем закоммитить metadata отдельным commit.
10. Создать и отправить GitHub repository через `gh repo create` с выбранной
   visibility, `--source`, `--remote=origin` и `--push`. Не менять существующий
   remote и не перезаписывать repository с совпавшим именем.

## Практики из базы Best Practices

1. Найти базу `Best Practices` среди соседних каталогов общего vault (папка с
   `README.md`, `INDEX.md` и `practices/`).
2. Действовать только с согласия пользователя (opt-in); ничего не устанавливать
   и не применять автоматически:
   - база найдена → предложить обновить её: `git pull` в каталоге базы;
   - база не найдена → предложить установить соседом в общий vault: `git clone
     git@github.com:NightMadMax/best-practices.git "../Best Practices"` из корня
     проекта (цель задаётся явно, чтобы совпадала со ссылкой `../Best Practices`
     в правиле нового проекта).
3. Если пользователь явно отказался, выполнить из корня стандарта
   `python3 scripts/best_practices_manifest.py --project <destination>
   --set-global optout`, проверить schema 2 manifest, **закоммитить файл**
   (чтобы отказ сохранился между машинами) и пропустить остальное — при отказе
   больше не предлагать. Не создавать schema 1 и не писать legacy-поля
   `optout`/`applied` вручную.
4. Если база доступна и пользователь согласен:
   - **Спросить стек(и) проекта.** Спросить, какие стеки планируется
     использовать (можно несколько), из списка Best Practices: `1c`, `web`,
     `backend`, `mobile`, `desktop`, `data-ml`, `data-analysis`,
     `excel-research`, `powerbi`, `jira-confluence`, `devops`, `embedded`.
     Если стек ещё неизвестен — разрешить пропустить (тогда только `common`).
   - Инициализировать manifest и записать выбранные стеки:
     `python3 scripts/best_practices_manifest.py --project <destination>
     --set-global ask --stack <stack1> --stack <stack2> …` (без `--stack` при
     неизвестном стеке).
   - Прочитать `<база>/.agents/skills/apply-best-practices/SKILL.md` и выполнить
     его **для `common` и каждого выбранного стека** (`--section <stack>` у
     `practice_report.py`). Если стек не выбран — только для `common`.
   - Изменения внести отдельным осмысленным commit и push; outcomes отдельных
     практик записывает только canonical `practice_report.py` из Best Practices
     в `practices`, без section-level `applied`.
5. Напомнить пользователю: если стек ещё не выбран или добавится новый — позже
   подтянуть стековые практики (правило в `AGENTS.md` нового проекта); стек можно
   дозаписать тем же `best_practices_manifest.py --stack <name>`.
6. Не менять стандарт `new-project-rules`; применять практики только в целевом
   проекте.

## Проверить результат

1. Запустить подходящие проверки нового проекта и проверить их exit codes,
   включая validator и migration status `up_to_date`, когда Python доступен.
2. Проверить `git status --short --branch`, `git remote -v` и наличие commit в
   `origin/main`.
3. Убедиться, что папка проекта находится внутри общего Obsidian vault, но сама
   не является vault.
4. Проверить instruction sources в новом процессе:
   `codex --cd <destination> --ask-for-approval never exec "Summarize the current instructions."`.
5. Сообщить путь, профиль, GitHub URL, commit и результаты проверок. Явно
   перечислить оставшиеся ручные действия или блокеры.
