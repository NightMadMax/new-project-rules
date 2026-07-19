---
type: implementation-plan
status: proposed
owner: project
last_verified: 2026-07-19
source_of_truth: repository
related:
  - "[[docs/architecture/ARCHITECTURE]]"
  - "[[docs/guides/CREATE_NEW_PROJECT]]"
  - "[[config/capabilities.tsv]]"
---

# План capability `1c` / «1С»

## Решение

`1c` — подключаемая capability, а не базовый профиль и не замена стеку Best
Practices `1c`. Она должна сочетаться с любым профилем и capability, включая
`jira-confluence`:

```yaml
profile: operated
capabilities: [1c, jira-confluence]
best_practices: [1c, jira-confluence]
```

Стек Best Practices доставляет инженерные практики, а capability — структуру
документации, проверку рабочего окружения, MCP-контракт, безопасные режимы и
проектные skills.

## Рабочая область с несколькими базами

Capability должна поддерживать верхнеуровневую папку 1С с несколькими
вложенными проектами/базами. Общие артефакты не должны смешивать контекст,
доступы и настройки конкретной базы.

```text
1C/
├── ONE_C_WORKSPACE.md
├── config/1c-projects.tsv
├── docs/operations/ENVIRONMENT_REGISTRY.md
├── docs/integrations/
└── configurations/
    ├── erp/
    │   └── PROJECT_1C.md
    ├── accounting/
    │   └── PROJECT_1C.md
    └── zup/
        └── PROJECT_1C.md
```

- Верхний уровень хранит общий реестр MCP, соглашения, интеграции и контуры.
- Вложенная папка хранит конфигурацию, расширения, версию платформы, EDT
  workspace, режим совместимости, профили и документацию конкретной базы.
- До любого действия агент обязан выбрать `project_id` и `environment_id`.
  При неоднозначности он останавливается и запрашивает выбор.
- Реальные строки соединения, пароли, токены, резервные копии и данные баз не
  записываются в Git.

### Жизненный цикл: bootstrap против runtime

Текущий механизм capability — это плоское копирование `source → destination`
из `config/capabilities.tsv` один раз при bootstrap (одна строка = один файл).
Он не умеет порождать заранее неизвестное число вложенных баз. Поэтому:

- **При bootstrap** создаётся только общий каркас `1C/`: `ONE_C_WORKSPACE.md`,
  пустой `config/1c-projects.tsv` с заголовком, `ENVIRONMENT_REGISTRY.md`,
  каталоги `docs/integrations/` и `configurations/` без баз.
- **Позже**, при добавлении конкретной базы, отдельный skill (`add-1c-base`
  либо соответствующий режим `select-1c-project`) инстанцирует
  `configurations/<base>/PROJECT_1C.md` из шаблона и добавляет строку в
  `config/1c-projects.tsv`. `PROJECT_1C.md` — это runtime-шаблон, не bootstrap-
  артефакт.
- Уникальность `project_id` и `environment_id` проверяет `validate-project.py`;
  дубликат идентификатора или контура — ошибка валидации, а не предупреждение.

## MCP-каталог и режимы

| Сервер | Назначение | Режим по умолчанию | Условие подключения |
|---|---|---|---|
| EDT MCP Server | EDT workspace, метаданные, BSL, ошибки, отладка, профилирование | analysis/review | EDT и совместимый плагин установлены |
| SyntaxCheckServer | Синтаксис BSL через BSL Language Server | read-only | Docker Desktop и лицензия |
| HelpSearchServer | Справка платформы конкретной версии | read-only | Docker, путь к документации платформы, embedding-модель |
| SSLSearchServer | Поиск по БСП | read-only | Docker, embedding-модель и известная версия БСП |
| TemplatesSearchServer | Шаблоны и ограниченная проектная память | read-only | Docker и утверждённая политика хранения памяти |
| 1C MCP Toolkit | Данные, метаданные и операции живой базы | analysis | явно выбранные проект и контур |
| 1CCodeChecker | Review и документация через 1С:Напарник | optional | отдельная подписка и секреты вне репозитория |

Ссылки на источники и инструкции сохраняются в capability-документации:

- <https://github.com/DitriXNew/EDT-MCP>
- <https://github.com/ROCTUP/1c-mcp-toolkit>
- <https://docs.onerpa.ru/mcp-servery-1c>

Установка контейнеров, регистрация MCP и ввод секретов выполняются только после
явного запроса пользователя. В templates и командах используются переменные
окружения, никогда не реальные ключи.

Совместимость патча `Run without update` и Toolkit привязана к версии MCP EDT
и платформы. В `docs/operations/TOOLCHAIN.md` фиксируется диапазон совместимых
версий, а не только обнаруженная версия.

## Безопасность

1. По умолчанию разрешены только инвентаризация, чтение, поиск и анализ.
2. `approved-write` требует явного подтверждения пользователя, выбранного
   контура, preflight и плана rollback.
3. Production не выбирается автоматически. Обновление конфигурации базы,
   восстановление базы, массовое изменение данных и выполнение произвольного
   BSL-кода запрещены без отдельного подтверждения.
4. Перед стартом и после него проверяется, что конфигурация базы не была
   обновлена. Если безопасный запуск без обновления не подтверждён, операция
   прекращается.
5. Toolkit и другие write-capable MCP не получают режим записи как общий
   дефолт capability.
6. `approved-write` не начинается, если не подтверждена свежая резервная копия
   выбранной базы. Backup остаётся ответственностью пользователя и вне Git;
   capability лишь требует подтверждения его наличия как предусловия.
7. Признак production хранится как атрибут контура в
   `docs/operations/ENVIRONMENT_REGISTRY.md`; `select-1c-project` читает его и
   запрещает неявный выбор production.

## Заимствуемая проверенная база проекта `1C`

Ниже перечислены артефакты, которые будут адаптированы, а не скопированы
буквально: их версии и пути относятся к конкретной машине и базе.

| Практика | Источник | План адаптации |
|---|---|---|
| EDT toolchain | `1C/TOOLS.md` | Реестр проверяемых версий и команд без локальных путей |
| Плагин обычного приложения EDT | `1C/docs/operations/EDT_ORDINARY_APPLICATION_PLUGIN.md` | Версионный preflight и инструкция установки/отката |
| Безопасный `Run without update` | `1C/docs/operations/EDT_MCP_RUN_WITHOUT_UPDATE_PATCH.md` | Optional patch только для совместимой версии MCP EDT |
| Два профиля EDT | `1C/docs/operations/EDT_DEBUGGING.md` | Шаблоны профилей без ID, имён баз и путей |
| Toolkit для обычного приложения | `1C/tools/mcp-toolkit-ordinary/` | Поставляемая project-local обработка и воспроизводимая сборка |
| Замеры EDT + Toolkit | `1C/docs/quality/PLAYBOOK.md` | Skill и отчёт с числовыми метриками |

Проверенная схема использует только два пользовательских профиля:

| Намерение | Профиль | Ограничение |
|---|---|---|
| Анализ данных базы | `Запуск Toolkit` | Автозапуск `.epf` через `/Execute`, затем health-check и реальный MCP-вызов |
| Отладка и измерение | `1С — обычное приложение (HTTP debug)` | Toolkit открывается в том же runtime; отдельный Attach-профиль не создаётся |

Динамические application ID, runtime UUID, alias базы и серверная debug-цель
всегда обнаруживаются текущим MCP EDT. Они не переносятся между базами.

Эта схема взята из базы на **обычном приложении**. Большинство современных баз —
управляемое приложение, поэтому плагин обычного приложения, `Run without update`
и HTTP-debug профиль поставляются как **опциональные** артефакты для legacy-баз,
а не как дефолт capability.

## Предлагаемые артефакты capability

- `ONE_C_WORKSPACE.md` — назначение общей области и реестр вложенных проектов.
- `config/1c-projects.tsv` — `project_id`, папка, конфигурация, платформа,
  EDT workspace, владелец и доступные контуры; без credentials.
- `docs/operations/ENVIRONMENT_REGISTRY.md` — назначение контуров, политика
  данных, backup и rollback.
- `PROJECT_1C.md` — карточка конкретной базы: конфигурация, расширения,
  совместимость и интеграции.
- `docs/operations/TOOLCHAIN.md` — обнаруженные версии, plugin/patch state и
  команды проверки.
- `docs/operations/DEPLOYMENT_MODEL.md` — поставка, обновление базы и rollback.
- `docs/quality/TEST_MODEL.md` — syntax, smoke, regression и performance.
- `docs/integrations/ONE_C_INTEGRATIONS.md` — HTTP, COM, файлы и обмены.

## Skills

1. `verify-1c-workspace` — проверяет EDT, платформу, Java, Docker/WSL,
   обязательный plugin, patch state, профили, свободные порты и MCP без
   установки или изменения состояния. На macOS корректно деградирует
   (сообщает о недоступном software), а не падает.
2. `select-1c-project` — выбирает `project_id` и `environment_id`; запрещает
   продолжение при неоднозначности или неявном production.
3. `query-1c-infobase` — выбирает безопасный профиль, запускает Toolkit,
   подтверждает health-check и оформляет доказательство фактического
   подключения (стандартное место — `docs/operations/`).
4. `measure-1c-performance` — фиксирует выборку и baseline, запускает
   Toolkit-таймеры и EDT profiling, возвращает total/average/min/max,
   ошибки, документов в секунду и структурный профиль.
5. `work-with-1c-edt` — BSL, конфигурации, расширения, валидация и безопасный
   lifecycle EDT.

Каждый skill поставляется с Codex-мостом `agents/openai.yaml` и `references/`
по образцу skills `jira-confluence`; глобальные правила Codex-first, поэтому
одного Claude `SKILL.md` недостаточно.

## Точки подключения в коде

Capability затрагивает те же места, что и `jira-confluence`; их надо изменить
согласованно, иначе `1c` не будет распознан:

- `config/capabilities.tsv` — строки bootstrap-артефактов capability.
- `scripts/project_metadata.py` — добавить `1c` в `CAPABILITY_NAMES`.
- `scripts/bootstrap-new-project.ps1` и `scripts/bootstrap-new-project.sh` —
  снять захардкоженный guard `= jira-confluence`; shell принимает capability
  одним позиционным `$4`, поэтому интерфейс надо переписать на **список**
  capability, чтобы поддержать связку `[1c, jira-confluence]`.
- `scripts/validate-project.py` — валидация артефактов `1c` и уникальности
  строк `config/1c-projects.tsv`.
- `.agents/skills/create-new-project/SKILL.md` — упоминание новой capability.

## Синхронизация документации (в той же задаче)

Правила `AGENTS.md` требуют обновлять в одной задаче со скриптами/skills:

- `INDEX.md`, `docs/README.md` (реестр секций), `CHANGELOG.md`.
- `docs/guides/CREATE_NEW_PROJECT.md` и `docs/guides/USE_THIS_PROJECT.md`.
- `docs/quality/DEFECTS.md`/`PLAYBOOK.md` — по мере обнаружения дефектов и
  проверенных паттернов capability.

## Этапы внедрения

1. Утвердить состав MCP, режимы `analysis`/`approved-write` и правила хранения
   project memory.
2. Добавить capability `1c` в manifest, schema, PowerShell и shell bootstrap;
   переписать однокапабилитный позиционный интерфейс shell на список и снять
   захардкоженные guards `= jira-confluence`, чтобы поддержать комбинацию
   capability.
3. Добавить templates и registry для общей рабочей области; развести
   bootstrap-каркас `1C/` и runtime-инстанцирование базы через `add-1c-base`.
4. Создать и валидировать пять project-local skills с Codex-мостами
   `agents/openai.yaml`.
5. Добавить preflight-скрипт без установки и без доступа к секретам.
6. Добавить MCP-инструкции и optional Docker deployment после отдельного
   утверждения состава, лицензий и хранилищ индексов.
7. Добавить regression tests: одиночная база, несколько баз, уникальность
   `project_id`/`environment_id`, сочетание с `jira-confluence`, отсутствие
   секретов и credentials-колонок в шаблонах и `1c-projects.tsv`, production
   guard, backup-precondition, деградация preflight на macOS и shell/PowerShell
   parity.
8. Обновить в той же задаче docs/guides/skills (см. «Синхронизация
   документации») и провести общий bootstrap/validator test и review каждого
   этапа.

## Критерии готовности

- Новый проект создаётся с `1c` отдельно либо совместно с `jira-confluence`.
- В общей рабочей области можно зарегистрировать несколько баз без смешения
  идентификаторов и окружений.
- Агент не выполняет write-операцию без явного выбора базы/контура и
  подтверждения.
- Preflight объясняет недостающий software/MCP без попытки установки.
- Templates, scripts и docs не содержат токенов, ключей, строк соединения,
  абсолютных машинных путей или названий рабочих баз; это проверяется тестом-
  сканером, а не только на ревью.
- Capability не предполагает обычное приложение по умолчанию: базы на
  управляемом приложении работают без опциональных legacy-артефактов.
- Preflight на macOS сообщает о недоступном 1С-software, а не завершается
  ошибкой.
- `approved-write` невозможен без подтверждённого backup и явно выбранного
  непроизводственного контура.
