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
   необходимости.
5. Проверить `AGENTS.md`, `CLAUDE.md=@AGENTS.md`, wikilinks, отсутствие
   `.obsidian`, абсолютных machine-specific paths и секретов.
6. Если доступен Python 3.9+, запустить read-only validator из корня правил:
   - macOS/Linux: `./scripts/validate-project.sh --root <destination> --kind project --profile <profile>`;
   - Windows: `.\scripts\validate-project.ps1 -Root <destination> -Kind project -Profile <profile>`.
   При отсутствии Python выполнить существующие ручные проверки и явно сообщить,
   что расширенная валидация пропущена; не устанавливать Python без разрешения.
7. Построить read-only plan adoption metadata с явным выбранным profile:
   - macOS/Linux: `./scripts/plan-migration.sh --plan --target project --root <destination> --profile <profile> --report-only`;
   - Windows: `.\scripts\plan-migration.ps1 -Plan -Target project -Root <destination> -Profile <profile> -ReportOnly`.
   Не создавать `.project-standard.json` вручную: текущий этап только показывает
   reviewable план и preconditions будущего apply.
8. Если bootstrap создал начальный commit до заполнения документов, сделать
   отдельный осмысленный commit с завершённой конфигурацией.
9. Создать и отправить GitHub repository через `gh repo create` с выбранной
   visibility, `--source`, `--remote=origin` и `--push`. Не менять существующий
   remote и не перезаписывать repository с совпавшим именем.

## Проверить результат

1. Запустить подходящие проверки нового проекта и проверить их exit codes,
   включая validator и migration plan, когда Python доступен.
2. Проверить `git status --short --branch`, `git remote -v` и наличие commit в
   `origin/main`.
3. Убедиться, что папка проекта находится внутри общего Obsidian vault, но сама
   не является vault.
4. Сообщить путь, профиль, GitHub URL, commit и результаты проверок. Явно
   перечислить оставшиеся ручные действия или блокеры.
