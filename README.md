# Правила для нового проекта

Переносимый набор правил и шаблонов для создания проектов внутри общего
Obsidian vault. Каждый проект является отдельной папкой, корнем собственного
git-репозитория и локальной копией отдельного GitHub-репозитория.

Markdown редактируется напрямую в папке проекта. REST API, helper,
синхронизация и вторая копия заметок не требуются.

## Кратко о проекте

Проект нужен для стандартизированного старта новых репозиториев, в которых
сразу согласованы:

- структура Markdown-документации;
- правила для AI-агентов через `AGENTS.md` и `CLAUDE.md`;
- работа внутри общего Obsidian vault без отдельной копии заметок;
- базовая Git/GitHub-инициализация и переносимость между компьютерами.

Практически это означает: вместо ручной сборки структуры проекта пользователь
запускает один из bootstrap-скриптов и получает готовый каркас с нужным
профилем документов, правилами агента и проверяемой структурой.

## Что проект делает

Проект:

- создаёт новый проект по одному из профилей: `minimal`, `software`,
  `operated`, `all`;
- заполняет обязательное ядро файлов: `README.md`, `PROJECT.md`, `INDEX.md`,
  `AGENTS.md`, `CLAUDE.md`;
- добавляет только релевантные условные документы и шаблоны;
- проверяет среду, структуру проекта и согласованность глобальных правил;
- строит и применяет управляемые migration-планы для project/global metadata;
- хранит единый машиночитаемый контракт профилей, policy и migrations.

## Как это реализовано

Технически проект опирается на три слоя:

1. `config/` и `STANDARD_VERSION` задают версию стандарта, состав профилей,
   policy literals и migration contract.
2. `scripts/` содержит переносимые shell/PowerShell entry points и общую
   Python-логику для validator, doctor, policy sync и migration planning.
3. `templates/new-project/` и `.agents/skills/` описывают, какие файлы должны
   быть созданы и как агент должен применять этот стандарт в новых проектах.

Идея простая: shell/PowerShell-обёртки дают удобный запуск на macOS/Linux и
Windows, а общая Python-логика удерживает единое поведение там, где нужна
нетривиальная проверка или планирование.

## Основные пользовательские команды

Первичная настройка глобальных правил на компьютере:

```sh
./scripts/setup-global-agents.sh
```

```powershell
.\scripts\setup-global-agents.ps1
```

Создать новый проект:

```sh
./scripts/bootstrap-new-project.sh "/path/to/New Project" "New Project" software
```

```powershell
.\scripts\bootstrap-new-project.ps1 -Destination "C:\Projects\New Project" -ProjectName "New Project" -Profile software
```

Проверить, что компьютер и проект соответствуют стандарту:

```sh
./scripts/project-doctor.sh --root . --agent-mode codex
./scripts/validate-project.sh --root . --kind rules
```

```powershell
.\scripts\project-doctor.ps1 -Root . -AgentMode codex
.\scripts\validate-project.ps1 -Root . -Kind rules
```

Проверить синхронизацию глобальных правил агента:

```sh
./scripts/sync-global-agents.sh --check
./scripts/sync-global-agents.sh --diff --report-only
```

```powershell
.\scripts\sync-global-agents.ps1 -Check
.\scripts\sync-global-agents.ps1 -Diff -ReportOnly
```

Построить или применить migration-план:

```sh
./scripts/plan-migration.sh --plan --target project --root "/path/to/project"
./scripts/plan-migration.sh --apply --target project --root "/path/to/project" --fingerprint "<64-hex>" --yes
```

```powershell
.\scripts\plan-migration.ps1 -Plan -Target project -Root "C:\Projects\Example"
.\scripts\plan-migration.ps1 -Apply -Target project -Root "C:\Projects\Example" -Fingerprint "<64-hex>" -Confirm
```

## Пользовательские команды

Ниже перечислены основные команды, которые пользователь реально запускает при
работе с этим стандартом.

### `setup-global-agents`

Команды:

```sh
./scripts/setup-global-agents.sh
```

```powershell
.\scripts\setup-global-agents.ps1
```

Для чего нужна:
Один раз настроить на компьютере общие глобальные правила для Codex и Claude
Code.

Что делает технически:

- создаёт `~/.codex/AGENTS.md`, если файла ещё нет, на основе
  [[GLOBAL_AGENT_INSTRUCTIONS]];
- не перезаписывает существующий `~/.codex/AGENTS.md`;
- создаёт `~/.claude/CLAUDE.md` с одной строкой `@~/.codex/AGENTS.md`;
- если `~/.claude/CLAUDE.md` был symlink на `~/.codex/AGENTS.md`, заменяет его
  на import;
- если в `~/.claude/CLAUDE.md` уже лежит другой контент, завершает работу с
  конфликтом и ничего не меняет.

### `bootstrap-new-project`

Команды:

```sh
./scripts/bootstrap-new-project.sh "/path/to/New Project" "New Project" software
```

```powershell
.\scripts\bootstrap-new-project.ps1 -Destination "C:\Projects\New Project" -ProjectName "New Project" -Profile software
```

Для чего нужна:
Создать новый проект по этому стандарту.

Что делает технически:

- читает `config/profiles.tsv` и определяет состав файлов для профиля
  `minimal`, `software`, `operated` или `all`;
- создаёт папку проекта, если она отсутствует или пуста;
- копирует шаблоны из `templates/new-project/` и подставляет имя проекта и
  текущую дату;
- генерирует `.gitignore`, `.gitattributes`, `.editorconfig` и `CLAUDE.md`;
- обновляет `INDEX.md` и `docs/README.md`, чтобы там появились wikilinks на
  созданные документы;
- если установлен Git, инициализирует новый репозиторий, переводит HEAD на
  `main`, делает `git add -A` и при наличии `user.name`/`user.email` создаёт
  первый commit;
- если bootstrap завершается ошибкой, удаляет частично созданный результат,
  чтобы не оставлять повреждённый проект.

### `add-agent-scope`

Команды:

```sh
./scripts/add-agent-scope.sh services/api "Run API tests before changing handlers."
```

```powershell
.\scripts\add-agent-scope.ps1 -Directory services/api -Rule "Run API tests before changing handlers."
```

Для чего нужна:
Добавить отдельные агентские правила для конкретного подкаталога внутри уже
существующего проекта.

Что делает технически:

- проверяет, что каталог находится внутри существующего git-проекта;
- создаёт `<subdir>/AGENTS.md`, если файла ещё нет;
- создаёт `<subdir>/CLAUDE.md` с одной строкой `@AGENTS.md`;
- не перезаписывает уже существующий scoped `AGENTS.md`;
- проверяет, что `CLAUDE.md` не конфликтует с другой конфигурацией;
- дописывает ссылки на scoped-файлы в корневой `INDEX.md`.

### `check-environment`

Команды:

```sh
./scripts/check-environment.sh both
```

```powershell
.\scripts\check-environment.ps1 -AgentMode both
```

Для чего нужна:
Быстро проверить, готов ли текущий компьютер к работе по этому стандарту.

Что делает технически:

- ничего не изменяет;
- проверяет наличие `git`, `gh`, `codex`, `claude` в зависимости от режима;
- проверяет, авторизован ли `gh`;
- проверяет настройку `git credential.helper`;
- проверяет наличие `~/.claude/CLAUDE.md` для Claude-сценария;
- отдельно показывает рекомендованные, но не обязательные инструменты:
  `python3`, `pwsh`, `rg`, `brew`.

### `validate-project`

Команды:

```sh
./scripts/validate-project.sh --root . --kind rules
./scripts/validate-project.sh --root "/path/to/project" --kind project --profile software
```

```powershell
.\scripts\validate-project.ps1 -Root . -Kind rules
.\scripts\validate-project.ps1 -Root "C:\Projects\Example" -Kind project -Profile software
```

Для чего нужна:
Проверить, соответствует ли проект или сам репозиторий правил требованиям
стандарта.

Что делает технически:

- ничего не изменяет;
- запускает общую Python-валидацию из `scripts/validate-project.py`;
- проверяет структуру файлов против `config/profiles.tsv`;
- проверяет frontmatter, wikilinks, локальные абсолютные пути, секреты и сырые
  каталоги памяти агентов;
- проверяет согласованность индексов, шаблонов, policy и metadata;
- умеет валидировать как этот репозиторий правил, так и уже созданный новый
  проект.

### `project-doctor`

Команды:

```sh
./scripts/project-doctor.sh --root . --agent-mode codex
```

```powershell
.\scripts\project-doctor.ps1 -Root . -AgentMode codex
```

Для чего нужна:
Сделать комплексную диагностику: сначала компьютера, затем проекта.

Что делает технически:

- запускает `check-environment`;
- затем запускает `validate-project.py` в doctor-режиме;
- если доступен Python 3.9+, печатает структурные замечания по проекту;
- в режиме `--report-only` всегда завершает работу без ошибки после печати
  отчёта;
- ничего не изменяет ни на компьютере, ни в проекте.

### `sync-global-agents`

Команды:

```sh
./scripts/sync-global-agents.sh --check
./scripts/sync-global-agents.sh --diff --report-only
```

```powershell
.\scripts\sync-global-agents.ps1 -Check
.\scripts\sync-global-agents.ps1 -Diff -ReportOnly
```

Для чего нужна:
Проверить, синхронизированы ли глобальные правила на компьютере с переносимым
эталоном из этого проекта.

Что делает технически:

- ничего не изменяет;
- сравнивает [[GLOBAL_AGENT_INSTRUCTIONS]] с `~/.codex/AGENTS.md`;
- распознаёт состояния `missing`, `legacy_exact`, `managed_match`,
  `managed_drift`, `unmanaged_conflict`, `malformed`;
- в режиме `--check` сообщает текущее состояние;
- в режиме `--diff` показывает secret-safe structural diff без вывода полного
  содержимого пользовательских правил;
- используется перед migration workflow для глобальных правил.

### `plan-migration`

Команды:

```sh
./scripts/plan-migration.sh --plan --target project --root "/path/to/project"
./scripts/plan-migration.sh --apply --target project --root "/path/to/project" --fingerprint "<64-hex>" --yes
./scripts/plan-migration.sh --plan --target global --report-only
```

```powershell
.\scripts\plan-migration.ps1 -Plan -Target project -Root "C:\Projects\Example"
.\scripts\plan-migration.ps1 -Apply -Target project -Root "C:\Projects\Example" -Fingerprint "<64-hex>" -Confirm
.\scripts\plan-migration.ps1 -Plan -Target global -ReportOnly
```

Для чего нужна:
Построить и при необходимости применить безопасную миграцию стандарта для
проекта или глобальных правил.

Что делает технически:

- читает `STANDARD_VERSION`, `config/migrations.tsv` и `config/profiles.tsv`;
- в режиме `--plan` ничего не меняет, а строит preview и fingerprint;
- для project target готовит `.project-standard.json`, если проект ещё legacy;
- для global target готовит adoption managed-block для `~/.codex/AGENTS.md`,
  если состояние допускает автоматическую миграцию;
- перед apply проверяет preconditions: чистый Git tree, допустимый профиль,
  валидные исходные данные и точное совпадение fingerprint;
- при записи использует atomic update, а для глобального файла предусматривает
  backup.

## Агентские команды

Это не shell-команды, а пользовательские команды для Codex и Claude Code,
которые используют этот стандарт через Agent Skills.

### `$create-new-project` / `/create-new-project`

Для чего нужна:
Попросить агента создать новый проект по этому стандарту.

Что делает технически:

- агент запускает bootstrap workflow;
- создаёт стартовые документы;
- инициализирует Git;
- при наличии доступа может создать GitHub-репозиторий и выполнить push;
- проверяет, что проект находится внутри общего Obsidian vault.

### `$setup-new-computer` / `/setup-new-computer`

Для чего нужна:
Попросить агента проверить и подготовить новый компьютер под этот workflow.

Что делает технически:

- агент проверяет обязательные инструменты;
- настраивает глобальные инструкции;
- запускает doctor и сопутствующую диагностику.

### `$promote-project-knowledge`

Для чего нужна:
Перенести проверенный общий урок из конкретного проекта обратно в этот
стандарт.

Что делает технически:

- агент обновляет правила, шаблоны, тесты или документацию этого репозитория;
- используется уже не для старта нового проекта, а для эволюции самого
  стандарта.

## Руководства

- [[docs/README|Документация проекта]]
- [[docs/guides/CREATE_NEW_PROJECT|Как создать новый проект]]
- [[docs/guides/SETUP_NEW_COMPUTER|Как подключить новый компьютер]]
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Как переносить знания между проектами]]
- [[docs/guides/VALIDATE_AND_DIAGNOSE|Как валидировать проект и запускать doctor]]
- [[docs/guides/SYNC_GLOBAL_AGENTS|Как проверить синхронизацию глобальных правил]]
- [[docs/guides/PLAN_MIGRATIONS|Как построить безопасный план миграции]]
- [[docs/security/THREAT_MODEL|Какие угрозы и supply-chain controls учитывает стандарт]]

## Скиллы Codex и Claude Code

- [[.agents/skills/setup-new-computer/SKILL|setup-new-computer]] — проверяет и
  настраивает новый компьютер по общим правилам.
- [[.agents/skills/create-new-project/SKILL|create-new-project]] — создаёт,
  проверяет и публикует новый проект.
- [[.agents/skills/promote-project-knowledge/SKILL|promote-project-knowledge]] —
  превращает проверенный общий урок в правило, шаблон, тест или автоматизацию.

Канонические workflow находятся в `.agents/skills/` и автоматически
обнаруживаются Codex. Claude Code обнаруживает тонкие мосты в `.claude/skills/`,
которые загружают те же канонические файлы без дублирования инструкций.

## Использование на другом компьютере

1. Клонировать этот репозиторий.
2. Клонировать репозиторий внутрь общей папки Obsidian vault и открыть в
   Obsidian саму общую папку, а не вложенный проект.
3. Перенести содержимое [[GLOBAL_AGENT_INSTRUCTIONS|глобальных инструкций]] в глобальный
   `~/.codex/AGENTS.md`, сохранив уже существующие инструкции этого компьютера.
4. Настроить глобальные правила для Claude Code (один раз на компьютер) —
   через импорт, без symlink. Скрипт создаёт `~/.claude/CLAUDE.md` с
   `@~/.codex/AGENTS.md`, не перезаписывает существующие инструкции и безопасен
   при повторном запуске:

   ```sh
   ./scripts/setup-global-agents.sh
   ```

   ```powershell
   .\scripts\setup-global-agents.ps1
   ```

   После настройки открыть Claude Code и выполнить `/memory`: список должен
   показывать глобальный `~/.claude/CLAUDE.md` и импортированные инструкции.
5. Для нового проекта запустить один из bootstrap-скриптов.

Навигация по проекту в общем vault: [[INDEX|индекс]], [[PROJECT|описание проекта]],
[[TEMPLATES|каталог шаблонов]].

macOS/Linux:

```sh
./scripts/bootstrap-new-project.sh "/path/to/New Project" "New Project" software
```

Windows PowerShell:

```powershell
.\scripts\bootstrap-new-project.ps1 -Destination "C:\Projects\New Project" -ProjectName "New Project" -Profile software
```

Профили:

- `minimal` — обязательное ядро (`README`, `AGENTS`, `CLAUDE`, `INDEX`,
  `PROJECT`) плюс `.editorconfig`, `.gitignore` и `.gitattributes`;
- `software` — ядро плюс индекс `docs/`, `CHANGELOG`, `ARCHITECTURE` и
  `TESTING`;
- `operated` — `software` плюс `ACTIONS`, `TOOLS`, `INTEGRATIONS` и
  `ENVIRONMENTS`;
- `all` — `operated` плюс `INTERFACES`, `DATA_MODEL`, `SECURITY` и
  `THREAT_MODEL`.

Канонический состав профилей и их связи с `INDEX.md`/`docs/README.md` хранит
`config/profiles.tsv`. Оба bootstrap-адаптера читают этот manifest напрямую;
parity-тесты проверяют фактический output на Windows и macOS/Linux.

Шаблоны «по одному файлу на экземпляр» — ADR, исследования, ревью, runbook и
postmortem — профиль намеренно не создаёт, чтобы не плодить пустые документы.
Они остаются в `templates/new-project/` и копируются вручную по мере
необходимости.

Bootstrap создаёт в каждом проекте `CLAUDE.md` из одной строки `@AGENTS.md`,
поэтому Codex (через `AGENTS.md`) и Claude Code (через `CLAUDE.md`) читают одни
и те же правила без дублирования. Созданный `AGENTS.md` требует давать все
ответы, исследования, ревью, планы и отчёты пользователю на русском языке,
если пользователь прямо не запросил другой язык. Все общие правила держите в
корневом `AGENTS.md`. Если подкаталогу нужны собственные правила, создайте рядом пару
`AGENTS.md` + `CLAUDE.md`, передав скрипту реальное правило:

```sh
./scripts/add-agent-scope.sh services/api "Run API tests before changing handlers."
```

```powershell
.\scripts\add-agent-scope.ps1 -Directory services/api -Rule "Run API tests before changing handlers."
```

Вложенные правила уточняют корневые и не должны им противоречить.

Создавайте проект внутри уже открытого общего Obsidian vault. Не превращайте
папку проекта в отдельный vault; создайте для неё отдельный GitHub-репозиторий
и подключите `origin`.

## Главное правило

Не копируйте в Markdown данные, для которых уже есть первичный
машиночитаемый источник: OpenAPI, lock-файл, SBOM или `CODEOWNERS`. Markdown
должен объяснять и связывать эти источники.

Markdown-заметки связываются через wikilinks. Запись имени файла в обратных
кавычках показывает код, но не создаёт ребро в графе Obsidian. При изменении
этого универсального набора одновременно обновляются
[[GLOBAL_AGENT_INSTRUCTIONS]], bootstrap и шаблоны.
