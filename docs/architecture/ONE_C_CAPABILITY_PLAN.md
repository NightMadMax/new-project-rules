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
   установки или изменения состояния.
2. `select-1c-project` — выбирает `project_id` и `environment_id`; запрещает
   продолжение при неоднозначности или неявном production.
3. `query-1c-infobase` — выбирает безопасный профиль, запускает Toolkit,
   подтверждает health-check и оформляет доказательство фактического
   подключения.
4. `measure-1c-performance` — фиксирует выборку и baseline, запускает
   Toolkit-таймеры и EDT profiling, возвращает total/average/min/max,
   ошибки, документов в секунду и структурный профиль.
5. `work-with-1c-edt` — BSL, конфигурации, расширения, валидация и безопасный
   lifecycle EDT.

## Этапы внедрения

1. Утвердить состав MCP, режимы `analysis`/`approved-write` и правила хранения
   project memory.
2. Добавить capability `1c` в manifest, schema, PowerShell и shell bootstrap;
   сделать выбор нескольких capabilities единообразным.
3. Добавить templates и registry для общей рабочей области и вложенных баз.
4. Создать и валидировать пять project-local skills.
5. Добавить preflight-скрипт без установки и без доступа к секретам.
6. Добавить MCP-инструкции и optional Docker deployment после отдельного
   утверждения состава, лицензий и хранилищ индексов.
7. Добавить regression tests: одиночная база, несколько баз, сочетание с
   `jira-confluence`, отсутствие секретов, production guard и shell/PowerShell
   parity.
8. Провести общий bootstrap/validator test и review каждого этапа.

## Критерии готовности

- Новый проект создаётся с `1c` отдельно либо совместно с `jira-confluence`.
- В общей рабочей области можно зарегистрировать несколько баз без смешения
  идентификаторов и окружений.
- Агент не выполняет write-операцию без явного выбора базы/контура и
  подтверждения.
- Preflight объясняет недостающий software/MCP без попытки установки.
- Templates, scripts и docs не содержат токенов, ключей, строк соединения,
  абсолютных машинных путей или названий рабочих баз.
