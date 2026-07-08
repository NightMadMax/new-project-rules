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

## Где смотреть команды

Детальные per-command инструкции и техническое поведение команд являются частью
гайдов под `docs/guides/` и не дублируются в верхнеуровневых файлах.

- [[docs/guides/USE_THIS_PROJECT|USE_THIS_PROJECT]] — пользовательский вход:
  как работать с этим проектом и какими фразами ставить задачи агенту.
- [[docs/guides/user-guide/USER_GUIDE|USER_GUIDE]] — простое сквозное
  руководство: установка, Obsidian vault и основные пользовательские сценарии.
- [[docs/guides/user-guide/workflows/README|Каталог workflow]] — визуальные
  пошаговые разборы процессов (полный процесс + workflow пользователя).
- [[docs/guides/MANUAL_SCRIPTS|MANUAL_SCRIPTS]] — справочник по ручному запуску
  скриптов: команды `sh`/`.ps1`, ключевые флаги и когда запускать вручную.
- [[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]] — первичная настройка
  компьютера, `setup-global-agents`, `check-environment`, `project-doctor`.
- [[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]] — создание нового
  проекта, `bootstrap-new-project`, `add-agent-scope`.
- [[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE]] — validator и
  doctor.
- [[docs/guides/SYNC_GLOBAL_AGENTS|SYNC_GLOBAL_AGENTS]] — проверка и diff
  глобальных правил.
- [[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]] — plan/apply migration
  workflow.

## Агентские команды

Пользовательские команды для агентов и их workflow описаны в:

- [[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]] — `$create-new-project`
  и `/create-new-project`;
- [[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]] —
  `$setup-new-computer` и `/setup-new-computer`;
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|AI_KNOWLEDGE_PORTABILITY]] — обмен
  опытом через Best Practices (пользователь) и maintainer-only
  `$promote-project-knowledge` / `$apply-promotion-candidate`.

## Руководства

- [[docs/README|Документация проекта]]
- [[docs/guides/user-guide/USER_GUIDE|Руководство пользователя]]
- [[docs/guides/USE_THIS_PROJECT|Как работать с этим проектом]]
- [[docs/guides/CREATE_NEW_PROJECT|Как создать новый проект]]
- [[docs/guides/ASSESS_EXISTING_PROJECT|Как оценить уже существующий проект относительно стандарта]]
- [[docs/guides/SETUP_NEW_COMPUTER|Как подключить новый компьютер]]
- [[docs/guides/STANDARDIZE_EXISTING_PROJECT|Как стандартизировать уже существующий проект]]
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
- [[.agents/skills/assess-existing-project/SKILL|assess-existing-project]] —
  выполняет read-only оценку legacy-проекта и строит decision report без
  изменения файлов.
- [[.agents/skills/standardize-existing-project/SKILL|standardize-existing-project]] —
  использует assessment и затем ведёт workflow приведения проекта к стандарту
  на месте или через новый проект по правилам.
- [[.agents/skills/promote-project-knowledge/SKILL|promote-project-knowledge]] —
  maintainer-only: затвердевает вызревшую практику соседней базы Best Practices в
  обязательное правило NPR.
- [[.agents/skills/apply-promotion-candidate/SKILL|apply-promotion-candidate]] —
  maintainer-only: применяет один approved-кандидат как checked-in изменение
  стандарта.
- [[.agents/skills/reflect-and-record/SKILL|reflect-and-record]] — превращает
  ошибку или поправку в записанный урок и маршрутизирует его в нужный артефакт.
- [[.agents/skills/compress-project/SKILL|compress-project]] — безопасно сжимает
  накопившийся «мусор»: механическая компрессия, консолидация docs и, по
  запросу, память агентов; архивирует, а не удаляет.

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

Вложенные правила специализируют или переопределяют корневые только для своего
поддерева; `AGENTS.override.md` намеренно заменяет instruction-файл на своём
уровне.

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
