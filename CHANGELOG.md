# Журнал изменений

## Unreleased

### Добавлено

- [[docs/research/PROJECT_AUDIT_2026-07-03|Повторный глубокий аудит проекта]]:
  полный regression и PowerShell прогон, live GitHub/security verification,
  проверка внешних ссылок и adversarial fixtures standardization workflow;
  дефекты 34–40 записаны в [[docs/quality/DEFECTS|DEFECTS]].
- Шаг «Консолидация журналов» в skill
  [[.agents/skills/reflect-and-record/SKILL|reflect-and-record]] и шаблон
  [[templates/new-project/DEFECTS.template|DEFECTS]]: при более чем ~30
  Fixed-записях старые переносятся в архив. Первая консолидация выполнена:
  записи 1–27 перенесены в [[docs/quality/DEFECTS_ARCHIVE|архив дефектов]].
- `.obsidian/` в генерируемый `.gitignore` (bootstrap sh/ps1,
  standardize-existing-project, локальный `.gitignore`) и заметка в
  [[docs/architecture/ARCHITECTURE|архитектуре]] о принадлежности `.obsidian/`
  уровню родительского vault (защита от повторения класса дефекта 15).
- Пакет B аудита 2026-07, правило бюджета цепочки инструкций (рекомендация 3):
  глобальные плюс проектные правила вместе ≤ ~300 непустых строк — во всех
  слоях правил; проверка `instructions.chain_budget` в `validate-project.py`
  для проектного `AGENTS.md` и `AGENTS.template.md` с регрессионными тестами.
- Правило «не запускать двух агентов одновременно в одной рабочей копии;
  параллельно — только в отдельных git worktrees» во всех слоях правил
  (рекомендация 5).
- Указания для skills (рекомендация 8): ключевые триггеры — в начало
  `description` SKILL.md, deprecated `~/.codex/prompts` не использовать — в
  [[docs/guides/AI_KNOWLEDGE_PORTABILITY|гайде о переносимости знаний]] и
  skill [[.agents/skills/apply-promotion-candidate/SKILL|apply-promotion-candidate]].
- Первый паттерн в [[docs/quality/PLAYBOOK|PLAYBOOK]]: refresh глобальной
  managed policy при `managed_drift` по паттерну engine (подтверждён дважды).

### Изменено

- Консолидированы формулировки в `GLOBAL_AGENT_INSTRUCTIONS.md` и `AGENTS.md`
  без потери правил, чтобы цепочка инструкций осталась в бюджете (299/300
  непустых строк); активный `~/.codex/AGENTS.md` обновлён по паттерну
  PLAYBOOK № 1, postcondition `managed_match` (см. [[ACTIONS]]).

### Исправлено

- Гайд [[docs/guides/USE_THIS_PROJECT|USE_THIS_PROJECT]] дополнен: Claude
  Code эквиваленты в секции knowledge promotion и workflow
  `reflect-and-record` (дефект 30).
- [[TOOLS|TOOLS.md]] ссылается на каталог скриптов в [[INDEX|INDEX]] и
  [[docs/quality/TESTING|TESTING]] и фиксирует исключения из правила
  парности `.sh`/`.ps1` (дефект 32).
- Раздел `Unreleased` нарезан в релиз `v1.10.0` (дефект 31).

## v1.10.0 — 2026-07-02

### Добавлено

- [[docs/guides/USE_THIS_PROJECT|Гайд «Как работать с этим проектом»]]:
  пользовательский вход с фразами для типовых задач и выбором workflow;
  ссылки добавлены в [[README|README]], [[INDEX|INDEX]] и
  [[docs/README|индекс документации]].
- [[docs/research/PROJECT_AUDIT_2026-07|Аудит проекта — июль 2026]]:
  внутренний аудит консистентности, сверка с актуальной документацией
  Codex CLI и Claude Code, community-практики; дефекты 28–32 записаны в
  [[docs/quality/DEFECTS|DEFECTS]], рекомендации приоритизированы.
- [[docs/quality/PROMOTION_CANDIDATES|Backlog promotion candidates]] как
  staging area между project lessons и checked-in standard artifacts.
- Skills [[.agents/skills/harvest-project-lessons/SKILL|harvest-project-lessons]]
  и [[.agents/skills/apply-promotion-candidate/SKILL|apply-promotion-candidate]]
  для двухшагового knowledge-promotion workflow: сначала harvesting и triage,
  затем реализация approved-кандидата в правила, шаблоны, тесты, guides или
  skills.
- [[.agents/skills/promote-project-knowledge/SKILL|promote-project-knowledge]]
  переписан в orchestration-layer над `harvest-project-lessons` и
  `apply-promotion-candidate`, чтобы не дублировать low-level workflow.
- [[docs/research/AGENT_RUNTIME_CAPABILITIES_2026|Исследование рантайм-возможностей
  Codex/Claude Code 2026]]: сверка стандарта с официальными моделями обоих
  агентов и приоритизированный план улучшений правил и настройки компьютера.
- Раздел `Done when` в шаблоне [[templates/new-project/AGENTS.template|AGENTS]]
  для явных критериев готовности и самопроверки агента.
- [[templates/new-project/PLAYBOOK.template|Шаблон Playbook]] и правило
  `Pattern Playbook` (во всех слоях правил и активном `~/.codex/AGENTS.md`):
  фиксировать проверенные удачные паттерны как success-аналог журнала дефектов.
- Раздел `Rule Authoring` (во всех слоях и `~/.codex/AGENTS.md`): как писать
  эффективные правила — компактность ~150 строк, negative-инструкции,
  command-first, группировка по задаче и тест recite-back (из community-практик).
- Правило `Reflexive Learning` (во всех слоях и `~/.codex/AGENTS.md`): после
  ошибки или поправки агент рефлексирует, обобщает урок и маршрутизирует его в
  DEFECTS / PLAYBOOK / AGENTS / promotion — замыкает петлю обучения.
- Skill [[.agents/skills/reflect-and-record/SKILL|reflect-and-record]] (канон +
  Claude-мост + регистрация в `test-skills`): вызываемая процедура рефлексии и
  записи урока для Codex и Claude Code.
- [[docs/research/AGENT_COMMUNITY_PRACTICES_2026|Исследование community-практик
  Claude Code и Codex]]: config-as-code инциденты, качество правил AGENTS.md,
  петля reflect-and-record и кандидаты на внедрение.
- Подтверждение Claude-специфики (settings keys, hooks events, `.claude/rules/`
  с `paths:`, subagents, MCP `.mcp.json`) по `code.claude.com/docs` в
  [[docs/research/AGENT_RUNTIME_CAPABILITIES_2026|исследовании]]; поправлены
  выдуманные `subagentStatusLine` и `disable-model-invocation` для субагентов.
- Immutable GitHub Actions SHA policy, weekly Dependabot updates и
  path-triggered/manual macOS smoke workflow.
- [[docs/security/THREAT_MODEL|Threat model]] bootstrap, Agent Skills, global
  policy, migrations, knowledge promotion и CI supply chain.
- Fingerprint-protected migration apply с повторной проверкой preconditions,
  atomic write, точным global backup и идемпотентным повторным запуском.
- [[ACTIONS|Журнал внешних действий]] для global marker adoption и rollback
  evidence.
- Plan-only migration engine с TSV manifest, clean-tree preconditions,
  reviewable project metadata preview и secret-safe global adoption plan.
- [[docs/architecture/PROJECT_STANDARD_SCHEMA|Schema `.project-standard.json`]]
  и [[docs/guides/PLAN_MIGRATIONS|руководство по migration planning]].
- Read-only managed-block parser и native wrappers для secret-safe
  `sync-global-agents --check/--diff` без изменения active global policy.
- [[docs/guides/SYNC_GLOBAL_AGENTS|Руководство по global policy sync]] со
  state model, marker grammar и стабильными exit codes.
- Read-only Python 3.9+ validator, native wrappers и project doctor для проверки
  profile contract, indexes, wikilinks, frontmatter, memory, paths, secrets,
  Git state и Obsidian placement.
- [[docs/guides/VALIDATE_AND_DIAGNOSE|Руководство по validator и doctor]] со
  стабильными exit codes и `report-only` режимом.
- `STANDARD_VERSION=1`, TSV contracts профилей/policy и parity-тесты, которые
  фиксируют текущие outputs до manifest-driven refactor.
- [[docs/architecture/decisions/ADR-0002-versioned-project-contract|ADR-0002]]
  о versioned contract, native bootstrap adapters и hybrid Python runtime для
  будущих validator/migrations.
- [[docs/research/STRATEGIC_EVOLUTION_PLAN|Стратегический план]] перехода к
  versioned contract, validator, global sync и безопасным migrations.
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Политика переноса знаний]] и skill
  `promote-project-knowledge`: локальные memory отделены от проверенных общих
  правил, а promotion требует источника, области применения и проверки.
- Универсальные Agent Skills `setup-new-computer` и `create-new-project` для
  Codex и Claude Code с единым каноническим workflow.
- [[docs/quality/DEFECTS|Реестр дефектов]] для обязательной фиксации найденных
  проблем и истории их исправления.
- `requirements-dev.txt` с `PyYAML` для официальных генератора и validator
  Agent Skills.

### Исправлено

- Дефект 28: активный `~/.codex/AGENTS.md` восстановлен из переносимой
  политики на обоих компьютерах (re-adoption managed markers и обновление
  managed block); операции зафиксированы в [[ACTIONS|ACTIONS]].
- Дефект 29: в [[docs/README|индекс документации]] добавлены отсутствовавшие
  research-файлы.

### Изменено

- В переносимые и проектные правила, активный `~/.codex/AGENTS.md` и шаблон
  AGENTS добавлены агент-рантайм-правила Codex: держать `AGENTS.md` компактным
  (лимит `project_doc_max_bytes`, 32 KiB), семантика `AGENTS.override.md`
  (полная замена уровня) и запрет менять `AGENTS.md`/`CLAUDE.md` в середине
  сессии (инвалидация prompt cache).
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Политика переноса знаний]] подкреплена
  официальной позицией OpenAI о локальности memories/sessions и предпочтении
  skills вместо deprecated custom prompts.
- Workflow token остаётся read-only, checkout credentials не сохраняются, а
  CI отклоняет mutable `uses:` references до запуска project tests.
- Shell и PowerShell bootstrap теперь получают profile composition и index
  relationships напрямую из `config/profiles.tsv`; hardcoded списки артефактов
  удалены без изменения существующих profile outputs.
- Bootstrap дополняет `docs/README.md` по выбранному профилю и откатывает
  частично созданный проект при ошибке, сохраняя исходный пустой destination.
- Environment check поддерживает режимы `codex`, `claude` и `both`, поэтому
  неиспользуемый агент больше не блокирует настройку компьютера.
- Scoped agent setup отклоняет path traversal до создания каталога.
- Глобальные и проектные шаблоны правил синхронизированы и теперь содержат
  единые требования Knowledge Promotion и Defect Tracking.
- CI запускает contract-тесты Agent Skills и проверяет обязательные блоки
  переносимых инструкций.
- Общая рабочая папка теперь является единым Obsidian vault, а каждый проект —
  вложенной папкой и отдельным git/GitHub-репозиторием.
- Bootstrap больше не создаёт `.obsidian` внутри проектов; правила, шаблоны,
  руководства и проверки приведены к новой структуре.

## v1.9.0 — 2026-06-28

### Исправлено

- Shell-скрипты корректно определяют своё расположение при прямом запуске,
  через `PATH` и символическую ссылку; убраны неоднозначные GNU-зависимые
  конструкции и ложное добавление в `INDEX.md` при ошибке `grep`.
- Bootstrap проверяет каждую Git-операцию, переносимо создаёт ветку `main`,
  различает отсутствие идентичности и реальную ошибку commit и явно сообщает
  об отсутствии Git.
- Проверка окружения не обращается к credential helper, если Git отсутствует.
- PowerShell-тест больше не принимает ошибку `git status` за чистое дерево.
- PowerShell parser-check в CI возвращает ошибку при невалидном синтаксисе.

### Добавлено

- Регрессионные сценарии Git-идентичности, ошибок Git и PATH-symlink, smoke-тесты
  global/scoped agent setup и проверка PowerShell-синтаксиса без зависимостей.
- [[docs/quality/TESTING|Матрица тестирования]] и
  [[docs/reviews/CODE_REVIEW_scripts_2026-06-28|отчёт ревью скриптов]].

### CI

- Добавлены минимальные `permissions`, отмена устаревших запусков и проверки в
  Windows PowerShell 5.1 и PowerShell 7. Глобальная тестовая Git-идентичность
  удалена, чтобы не маскировать отрицательные сценарии.

## v1.8.1 — 2026-06-28

### Изменено

- В глобальные правила и шаблон `AGENTS.md` добавлено обязательное использование
  русского языка для ответов, исследований, ревью, планов и отчётов. Другой
  язык используется только по прямой просьбе пользователя; технические
  литералы сохраняются без искажения.
- Shell- и PowerShell-тесты bootstrap проверяют наличие языкового правила во
  всех создаваемых профилях.

## v1.8.0 — 2026-06-28

### Добавлено

- `scripts/test-bootstrap.sh` и `.ps1` — закоммиченный регрессионный тест
  генератора: создаёт проект каждого профиля во временной папке и проверяет
  инварианты (ядро, `CLAUDE.md=@AGENTS.md`, отсутствие BOM и подстановка
  плейсхолдеров, чистое git-дерево, состав по профилям, guard-ы). 77 проверок.
- `.github/workflows/ci.yml` — CI на каждый push/PR: `sh -n` и тест на Ubuntu,
  parse-check `.ps1` и тест на Windows. Реальные проверки, а не пустой workflow.

## v1.7.0 — 2026-06-28

### Исправлено

- Описание профилей в README приведено в соответствие с фактическим
  поведением bootstrap; добавлено пояснение, что шаблоны ADR, исследований,
  ревью, runbook и postmortem не создаются профилем, а копируются по требованию.

### Изменено

- Bootstrap делает начальный коммит после `git init`, поэтому новый проект не
  остаётся с несохранёнными файлами. Если git-идентичность не настроена,
  репозиторий инициализируется без коммита с понятной подсказкой.

## v1.6.0 — 2026-06-28

### Добавлено

- `.editorconfig` включён в обязательное ядро: создаётся bootstrap во всех
  профилях и добавлен в сам набор. Это единственный языко-нейтральный
  formatting-baseline без зависимостей (UTF-8, LF, финальный перевод строки,
  trim trailing whitespace; исключения для `*.md`, `*.ps1`, Makefile, `*.go`).
- `scripts/check-environment.sh` и `.ps1` — read-only проверка обязательной
  базы (`git`, `gh`, Codex, Claude Code, `gh auth`, credential helper) с
  отдельным выводом рекомендуемого (Python, `pwsh`, `rg`, Homebrew/WinGet).

### Обоснование

- Реализованы пункты 1–2 рекомендаций
  [[docs/research/MUST_HAVE_PROJECT_TOOLING_2026|исследования базы инструментов]].

## v1.5.0 — 2026-06-27

### Добавлено

- [[docs/research/MUST_HAVE_PROJECT_TOOLING_2026|Исследование обязательной базы
  инструментов проекта в 2026 году]]: критерии must-have, первичные источники,
  матрица решений для macOS/Windows и рекомендации к следующей версии
  bootstrap.

### Подтверждено

- Git, GitHub CLI, Codex, Claude Code, безопасное хранение credentials и
  системная командная среда составляют обязательное ядро рабочего компьютера.
- Python 3, PowerShell 7, standalone `ripgrep`, CI, containers и языковые
  инструменты должны оставаться рекомендуемыми или условными, а не скрытыми
  зависимостями каждого проекта.

## v1.4.0 — 2026-06-27

### Добавлено

- [[docs/README|docs/README.md]]: отдельный индекс папки документации и
  стандартная структура тематических каталогов.
- Bootstrap-профили `software`, `operated` и `all` теперь создают
  `docs/README.md` из отдельного шаблона и добавляют его в корневой [[INDEX]].
- [[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]]: создание нового vault,
  выбор bootstrap-профиля, заполнение документов и публикация в GitHub.
- [[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]]: подготовка macOS или
  Windows, GitHub-авторизация, глобальные правила Codex/Claude и подключение
  существующих проектов.

### Изменено

- [[README]] и [[INDEX]] дополнены ссылками на эксплуатационные руководства.

## v1.3.1 — 2026-06-27

### Исправлено

- Активные глобальные правила Codex приведены к import-модели без symlink.
- Setup-скрипты заменяют только symlink, указывающий на канонический
  `~/.codex/AGENTS.md`; другие ссылки и файлы считаются конфликтом.
- Идемпотентность проверяется по точному однострочному импорту, поэтому import
  внутри code block больше не даёт ложный успех.
- Scoped-скрипты требуют реальное правило вместо пустого placeholder и
  добавляют обе новые заметки в корневой [[INDEX]].
- Уточнено, что вложенные инструкции дополняют слои выше и не должны им
  противоречить.
- Добавлено правило выбора инструментов: существующий стек проекта и
  стандартные средства имеют приоритет; Python 3 standard library
  предпочтителен для нетривиальной кроссплатформенной автоматизации, когда он
  гарантированно доступен на всех целевых машинах.
- Если отсутствующий инструмент существенно лучше доступных замен, агент
  должен объяснить выбор и запросить разрешение на установку, а не молча
  использовать менее качественный обходной путь.

### Добавлено

- Установлен PowerShell 7.6.3 через Homebrew для runtime-проверки `.ps1`;
  сведения об инструменте и оставшемся Windows 5.1 coverage gap записаны в
  [[TOOLS]].

### Проверено

- Для shell-версий проверены пустая установка, повторный запуск, обычный
  конфликт, посторонний symlink, import внутри code block и повторное создание
  scoped-правил без дубликатов и частичных изменений.
- PowerShell-версии проверены статически; runtime PowerShell на текущем Mac
  первоначально отсутствовал, затем установлен с разрешения пользователя.
- Runtime-тест выявил и исправил конфликт локальной переменной `$isWindows` со
  встроенной read-only переменной PowerShell `$IsWindows`.
- Относительный путь scoped-правил теперь вычисляется через git, чтобы macOS
  path aliases (`/var` и `/private/var`) не давали ложный выход за project root.
- PowerShell parser, bootstrap, UTF-8 без BOM, global setup, symlink conflicts,
  fenced imports и scoped-index сценарии прошли runtime-проверку.

## v1.3.0 — 2026-06-27

### Добавлено

- `scripts/setup-global-agents.sh` и `.ps1` — безопасная идемпотентная настройка
  глобальных правил Codex+Claude: создают `~/.codex` и `~/.claude`, не
  перезаписывают существующие инструкции, останавливаются при конфликте.
- `scripts/add-agent-scope.sh` и `.ps1` — пара `AGENTS.md` + `CLAUDE.md` для
  правил отдельного подкаталога; описано правило вложенных инструкций.

### Изменено

- Импорт `@AGENTS.md` стал единым механизмом на всех ОС; symlink больше не
  основной способ (в README и глобальных инструкциях).
- PowerShell-bootstrap пишет UTF-8 без BOM через `System.IO.File` вместо
  `Set-Content -Encoding utf8`.
- Секция `Commands` в шаблоне AGENTS не содержит фиктивных команд: только
  проверенные в репозитории, иначе секция удаляется.
- `CLAUDE.md` возвращён в граф Obsidian в обоих индексах
  (`[[CLAUDE|CLAUDE.md]] | Imports [[AGENTS]] for Claude Code`).
- `.gitignore` (репозиторий и bootstrap) игнорирует только локальные файлы
  Claude: `CLAUDE.local.md`, `.claude/settings.local.json`,
  `.claude/scheduled_tasks.lock`; общие `.claude/` ресурсы коммитятся.

## v1.2.1 — 2026-06-27

### Добавлено

- В шаблон [[templates/new-project/AGENTS.template|AGENTS]] добавлена секция
  `Commands` в начале файла: команды установки, сборки, тестов, линта и запуска
  выносятся вперёд, как рекомендуют практики 2026 года.

### Изменено

- Формулировки в PROJECT, INDEX и ARCHITECTURE сделаны агент-нейтральными
  (Codex → агент), специфичные пути `~/.codex/AGENTS.md` сохранены.

## v1.2.0 — 2026-06-27

### Добавлено

- Поддержка Claude Code наряду с Codex: bootstrap создаёт в каждом проекте
  `CLAUDE.md` из одной строки `@AGENTS.md`, без дублирования правил.
- В README описан разовый глобальный шаг связывания `~/.claude/CLAUDE.md` с
  `~/.codex/AGENTS.md`.

### Изменено

- `GLOBAL_AGENT_INSTRUCTIONS`, `AGENTS.md`, шаблоны AGENTS и INDEX отражают, что
  `AGENTS.md` — единственный источник правил, а `CLAUDE.md` лишь импортирует его.
- В сам набор добавлен `CLAUDE.md` (dogfood) и запись о нём в `INDEX`.

## v1.1.0 — 2026-06-27

### Изменено

- Основные документы связаны Obsidian wikilinks и отображаются единым графом.
- Добавлен [[TEMPLATES|каталог шаблонов]], связывающий все template notes.
- Bootstrap-скрипты теперь создают связанные записи в [[INDEX]].
- В глобальные и переносимые инструкции добавлено правило одновременно
  обновлять базовые правила Codex, bootstrap и шаблоны при изменении стандарта.

### Проверено

- Подтверждено наличие внутренних ссылок между индексом, проектом,
  архитектурой, ADR, исследованием и шаблонами.

## v1.0.0 — 2026-06-27

### Добавлено

- Переносимый проект правил для Codex, Obsidian и GitHub.
- Глобальные и проектные инструкции.
- Двухуровневая модель документации: обязательное ядро и условные наборы.
- Шаблоны архитектуры, ADR, исследований, ревью, эксплуатации, качества, API,
  данных и безопасности.
- Bootstrap-скрипты для macOS/Linux и Windows.

### Проверено

- Папка проекта является Obsidian vault и git-root.
- В файлах отсутствуют секреты и абсолютные пути конкретного компьютера.
