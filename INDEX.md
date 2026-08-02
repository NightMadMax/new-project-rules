# Индекс

| Путь | Назначение |
|---|---|
| [[README|README.md]] | Использование набора на новом компьютере |
| [[OVERVIEW|OVERVIEW.md]] | Краткое описание набора для коллег |
| [[AGENTS|AGENTS.md]] | Правила агента для этого проекта |
| [[CLAUDE|CLAUDE.md]] | Imports [[AGENTS]] for Claude Code |
| [[GLOBAL_AGENT_INSTRUCTIONS|GLOBAL_AGENT_INSTRUCTIONS.md]] | Переносимый блок глобальных инструкций агента |
| [[PROJECT|PROJECT.md]] | Цели, scope, ограничения и критерии успеха |
| [[ACTIONS|ACTIONS.md]] | Журнал значимых действий вне Git и rollback evidence |
| `STANDARD_VERSION` | Версия схемы project standard |
| `config/profiles.tsv` | Канонический состав bootstrap-профилей и index relationships |
| `config/capabilities.tsv` | Канонический состав подключаемых возможностей проекта, класс доставки и владение каждым артефактом |
| `config/policy-contract.tsv` | Обязательные policy literals в переносимых правилах |
| `config/migrations.tsv` | Migration IDs, targets, schema transitions и handlers |
| `config/skills.tsv` | Реестр skills: класс проверки, корень, необходимость Claude-моста |
| `config/presets.tsv` | Раскрытие preset создания: минимальный профиль, capability и стеки практик |
| `config/capability-core.tsv` | Ядро capability: минимальный профиль и обязательный стек практик |
| `config/standard-source.txt` | Канонический owner/repository без credentials и локальных путей |
| [[CHANGELOG|CHANGELOG.md]] | Заметные изменения набора правил |
| [[CHANGELOG_ARCHIVE|CHANGELOG_ARCHIVE.md]] | Архив старых релизов, перенесённых при компрессии |
| [[TOOLS|TOOLS.md]] | Установленные инструменты, версии и команды проверки |
| `requirements-dev.txt` | Python-зависимости для сопровождения Agent Skills |
| [[docs/README|docs/README.md]] | Индекс отдельной папки документации |
| [[docs/guides/user-guide/README|user-guide/]] | Папка руководства пользователя: основной гайд + каталог визуальных workflow по процессам |
| [[docs/guides/user-guide/USER_GUIDE|USER_GUIDE.md]] | Основное пользовательское руководство: установка, ежедневные сценарии и безопасные запросы агенту |
| [[docs/guides/user-guide/workflows/README|workflows/]] | Каталог process-workflow: полный процесс + workflow пользователя (Markdown + HTML) |
| [[docs/guides/user-guide/workflows/best-practices-full|best-practices-full.md]] | Работа с практиками — полный процесс: все роли, запуск, вход/результат, сигнал |
| [[docs/guides/user-guide/workflows/best-practices-user|best-practices-user.md]] | Работа с практиками — workflow пользователя: что сделать, чтобы добиться результата |
| [[docs/guides/user-guide/workflows/best-practices-admin|best-practices-admin.md]] | Одобрение и применение практик — workflow администратора: разбор кандидатов, затвердевание, pin |
| [[docs/guides/user-guide/workflows/setup-new-computer-user|setup-new-computer-user.md]] | Настройка нового компьютера — workflow пользователя: два маршрута (агенту/вручную) |
| [[docs/guides/user-guide/workflows/projects-user|projects-user.md]] | Работа с проектами — карта действий пользователя: создание проекта + каталог действий |
| [[docs/guides/USE_THIS_PROJECT|USE_THIS_PROJECT.md]] | Пользовательский вход: как работать с проектом и какими фразами ставить задачи агенту |
| [[docs/guides/GITHUB_WORKFLOW|GITHUB_WORKFLOW.md]] | Правила прямого push, ролей, rulesets, required checks и GitHub API tokens |
| [[docs/guides/MANUAL_SCRIPTS|MANUAL_SCRIPTS.md]] | Справочник по ручному запуску скриптов: команды sh/ps1, флаги и когда запускать вручную |
| [[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT.md]] | Создание проекта вручную или по запросу агенту |
| [[docs/guides/ASSESS_EXISTING_PROJECT|ASSESS_EXISTING_PROJECT.md]] | Read-only оценка legacy-проекта и decision report без изменения файлов |
| [[docs/guides/STANDARDIZE_EXISTING_PROJECT|STANDARDIZE_EXISTING_PROJECT.md]] | Выбор стратегии для legacy-проекта: adoption in place или новый проект по стандарту |
| [[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER.md]] | Настройка нового macOS/Windows-компьютера |
| [[docs/guides/AI_KNOWLEDGE_PORTABILITY|AI_KNOWLEDGE_PORTABILITY.md]] | Двухъярусная модель знаний: опыт → Best Practices, стандарт NPR — maintainer-only |
| [[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE.md]] | Read-only validator, doctor и exit codes |
| [[docs/guides/SYNC_GLOBAL_AGENTS|SYNC_GLOBAL_AGENTS.md]] | Managed-block states, secret-safe check и diff глобальных правил |
| [[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS.md]] | Read-only project/global migration plans и preconditions |
| [[docs/architecture/ARCHITECTURE|ARCHITECTURE.md]] | Архитектура переносимого набора |
| [[docs/architecture/BEST_PRACTICES_CONTRACT|BEST_PRACTICES_CONTRACT.md]] | Pinned compatibility contract NPR ↔ Best Practices и процедура обновления |
| [[docs/architecture/PROJECT_STANDARD_SCHEMA|PROJECT_STANDARD_SCHEMA.md]] | Schema `.project-standard.json` и provenance invariants |
| [[docs/architecture/ONE_C_CAPABILITY_PLAN|ONE_C_CAPABILITY_PLAN.md]] | Принятый план capability `1c`: MCP, EDT, Toolkit, несколько баз и безопасность |
| [[docs/architecture/one-c/ENVIRONMENT_SETUP_PLAN|ENVIRONMENT_SETUP_PLAN.md]] | Принятый подплан среды capability `1c`: компоненты, EDT 2026, setup и Windows prerequisites |
| [[docs/architecture/one-c/DELIVERY_AND_STATE_PLAN|DELIVERY_AND_STATE_PLAN.md]] | Принятый подплан доставки capability `1c`: классы payload, `capability_artifacts`, ledger, версии и bump схемы |
| [[docs/architecture/one-c/IMPLEMENTATION_PLAN|IMPLEMENTATION_PLAN.md]] | План реализации capability `1c`: этапы Э1–Э10 в порядке выполнения, приёмка, архитектурное ревью и веха Windows |
| [[docs/architecture/decisions/ADR-0001-two-level-documentation|ADR-0001]] | Решение о двухуровневой документации |
| [[docs/architecture/decisions/ADR-0002-versioned-project-contract|ADR-0002]] | Решение о TSV contract и hybrid runtime |
| [[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture|ADR-0003]] | Двухъярусная архитектура знаний: роли, маршрутизация, managed/unmanaged, судьба скиллов |
| [[docs/research/PROJECT_ARTIFACT_MODEL|PROJECT_ARTIFACT_MODEL.md]] | Обоснование структуры артефактов |
| [[docs/research/MUST_HAVE_PROJECT_TOOLING_2026|MUST_HAVE_PROJECT_TOOLING_2026.md]] | Исследование обязательной базы инструментов в 2026 году |
| [[docs/research/STRATEGIC_EVOLUTION_PLAN|STRATEGIC_EVOLUTION_PLAN.md]] | Реализованный план policy-системы и следующий продуктовый этап |
| [[docs/research/CONSUMER_STANDARD_MEASUREMENT|CONSUMER_STANDARD_MEASUREMENT.md]] | Протокол измерения результата стандарта на consumer-проектах |
| [[docs/research/CONSUMER_STANDARD_BASELINE_2026-07-10|CONSUMER_STANDARD_BASELINE_2026-07-10.md]] | Первый проверенный baseline consumer-метрик |
| [[docs/research/AGENT_RUNTIME_CAPABILITIES_2026|AGENT_RUNTIME_CAPABILITIES_2026.md]] | Рантайм-возможности Codex/Claude Code и план улучшений правил |
| [[docs/research/AGENT_COMMUNITY_PRACTICES_2026|AGENT_COMMUNITY_PRACTICES_2026.md]] | Community-практики Claude Code/Codex и кандидаты на внедрение |
| [[docs/research/PROJECT_AUDIT_2026-07-03|PROJECT_AUDIT_2026-07-03.md]] | Повторный глубокий аудит: adversarial standardization checks, CI, portability и readiness |
| [[docs/research/BEST_PRACTICES_INTEGRATION|BEST_PRACTICES_INTEGRATION.md]] | Решения по интеграции базы Best Practices в create-new-project |
| [[docs/research/NPR_BP_KNOWLEDGE_ARCHITECTURE_2026-07-06|NPR_BP_KNOWLEDGE_ARCHITECTURE_2026-07-06.md]] | Архитектура знаний между new-project-rules и Best Practices: дублирование, маршрутизация, SSOT |
| [[docs/research/GENERAL_TRANSCRIBE_SKILL_PLAN|GENERAL_TRANSCRIBE_SKILL_PLAN.md]] | План общего skill transcribe (реализован): локальный Whisper, outputs, зависимости и проверки |
| [[docs/research/archive/README|Research archive]] | Устаревшие аудиты и завершённые исследования NPR ↔ Best Practices |
| [[docs/reviews/CODE_REVIEW_scripts_2026-06-28|CODE_REVIEW_scripts_2026-06-28.md]] | Ревью shell-, PowerShell-скриптов и CI |
| [[docs/reviews/NPR_BP_CLOSEOUT_REVIEW_2026-07-08|NPR_BP_CLOSEOUT_REVIEW_2026-07-08.md]] | Финальный live-аудит и закрытие программы NPR ↔ Best Practices |
| [[docs/reviews/REVIEW_2026-08-01_NPR|REVIEW_2026-08-01_NPR.md]] | Ревью всего NPR пятью независимыми срезами |
| [[docs/reviews/REVIEW_2026-08-02_ARCHITECTURE|REVIEW_2026-08-02_ARCHITECTURE.md]] | Архитектурное ревью: проверка утверждений стандарта против кода |
| [[docs/reviews/archive/README|Review archive]] | Промежуточные review завершённых фаз NPR ↔ Best Practices |
| [[docs/quality/TESTING|TESTING.md]] | Матрица и команды проверки скриптов |
| [[docs/quality/READINESS_1C\|docs/quality/READINESS_1C.md]] | Матрица готовности capability `1c`: критерий, статус, доказательство |
| [[docs/quality/RUNTIME_SMOKE_1C\|docs/quality/RUNTIME_SMOKE_1C.md]] | Протокол runtime smoke 1С на Windows (веха W) |
| [[docs/quality/DEFECTS|DEFECTS.md]] | Реестр обнаруженных и исправленных дефектов |
| [[docs/quality/DEFECTS_ARCHIVE|DEFECTS_ARCHIVE.md]] | Архив консолидированных Fixed-записей журнала дефектов |
| [[docs/quality/PLAYBOOK|PLAYBOOK.md]] | Реестр проверенных удачных паттернов и повторяемых good practices |
| [[docs/quality/PROMOTION_CANDIDATES|PROMOTION_CANDIDATES.md]] | Maintainer-only очередь затвердевания практик Best Practices в правила NPR |
| [[docs/quality/promotion-candidates/README|promotion-candidates/]] | Канонический one-file-per-candidate backlog и команды генератора |
| [[docs/quality/promotion-candidates/archive/README|promotion-candidates archive]] | Архив implemented/rejected promotion candidates |
| [[docs/security/THREAT_MODEL|THREAT_MODEL.md]] | Bootstrap, policy, migrations и CI supply-chain threats |
| [[TEMPLATES|TEMPLATES.md]] | Каталог и назначение всех шаблонов |
| [[.agents/skills/setup-new-computer/SKILL|setup-new-computer]] | Универсальный workflow настройки компьютера |
| [[.agents/skills/create-new-project/SKILL|create-new-project]] | Универсальный workflow создания проекта |
| [[.agents/skills/assess-existing-project/SKILL|assess-existing-project]] | Read-only оценка существующего проекта относительно стандарта |
| [[.agents/skills/standardize-existing-project/SKILL|standardize-existing-project]] | Выбор и выполнение стратегии стандартизации существующего проекта |
| [[.agents/skills/apply-promotion-candidate/SKILL|apply-promotion-candidate]] | Maintainer-only: перенос одного approved-кандидата в checked-in артефакты стандарта |
| [[.agents/skills/promote-project-knowledge/SKILL|promote-project-knowledge]] | Maintainer-only: затвердевание вызревшей практики Best Practices в правило NPR |
| [[.agents/skills/reflect-and-record/SKILL|reflect-and-record]] | Рефлексия ошибки/поправки и запись урока в нужный артефакт |
| [[.agents/skills/compress-project/SKILL|compress-project]] | Безопасная компрессия накопившегося «мусора»: журналы, docs, память |
| [[.agents/skills/document-process-workflow/SKILL|document-process-workflow]] | Создание и поддержание в актуальности workflow-отчётов процессов (docs/guides/user-guide/workflows) |
| `scripts/bootstrap-new-project.sh` | Создание проекта на macOS/Linux |
| `scripts/bootstrap-new-project.ps1` | Создание проекта в Windows PowerShell |
| `scripts/setup-global-agents.sh` | Глобальная настройка Codex+Claude (macOS/Linux) |
| `scripts/setup-global-agents.ps1` | Глобальная настройка Codex+Claude (Windows) |
| `scripts/add-agent-scope.sh` | Правила для подкаталога (macOS/Linux) |
| `scripts/add-agent-scope.ps1` | Правила для подкаталога (Windows) |
| `scripts/check-environment.sh` | Проверка обязательной базы инструментов (macOS/Linux) |
| `scripts/check-environment.ps1` | Проверка обязательной базы инструментов (Windows) |
| `scripts/cli_discovery.py` | Поиск CLI по запускаемости: все совпадения `PATH`, места установки вне его, `skipped` с причиной |
| `scripts/check-cli.sh` | POSIX-обёртка поиска CLI |
| `scripts/check-cli.ps1` | PowerShell-обёртка поиска CLI |
| `scripts/lib/Find-Python.ps1` | Единственное определение «пригодного Python» для всех PowerShell-обёрток |
| `scripts/test-powershell-wrappers.ps1` | Тесты обёрток: заглушка не выбирается, рабочий интерпретатор за ней находится |
| `scripts/test-cli-discovery.py` | Тесты обнаружения: заглушка не запускается, рабочий бинарник за ней находится |
| `config/1c-routing.tsv` | Маршрут каждой группы файлов upstream `ai_rules_1c` со ссылкой на решение плана |
| `config/1c-upstream-inventory.txt` | Список tracked-файлов upstream на закреплённом commit — контрольная сумма приёмки маршрутизации |
| `scripts/import_1c_upstream.py` | Разворачивает маршруты в строки ledger по локальному чекауту upstream |
| `scripts/one_c_agents.py` | Компиляция agent-проекций Codex и Claude по спецификации upstream-адаптеров |
| `scripts/one_c_adaptations.py` | Применение объявленных адаптаций upstream: якорь обязан совпасть ровно один раз |
| `config/1c-adaptations/` | Адаптации upstream-файлов: замены, решение плана и причина, по одной на файл |
| `config/1c-release.json` | Паспорт release capability `1c`: версия, pinned источники, зависимости, MCP-роли |
| `config/1c-artifacts.tsv` | Ledger: строка на каждый source-файл с действием, владением, целью и хэшами |
| `scripts/test-1c-upstream-routing.py` | Проверяет покрытие 241 файла маршрутами и саму развёртку |
| `scripts/test-bootstrap.sh` | Регрессионный тест bootstrap (macOS/Linux) |
| `scripts/test-bootstrap.ps1` | Регрессионный тест bootstrap (Windows) |
| `scripts/test-contract.sh` | Parity contract и bootstrap outputs (macOS/Linux) |
| `scripts/test-contract.ps1` | Parity contract и bootstrap outputs (Windows) |
| `scripts/validate-project.py` | Общая read-only validation logic на Python 3.9+ |
| `scripts/check_skills.py` | Проверка skills по `config/skills.tsv`: canonical-триада и vendored payload по hash |
| `scripts/artifacts_ledger.py` | Контракт и валидация ledger `.project-standard-artifacts.json` |
| `scripts/capability_artifacts.py` | Транзакционные план и применение артефактов capability |
| `scripts/presets.py` | Раскрытие preset в профиль, capability и стеки |
| `scripts/release_manifest.py` | Контракт release capability: паспорт, ledger артефактов, `release_id` |
| `scripts/build-capability-release.py` | Сборка и проверка release против локального staging |
| `scripts/check-upstream-sources.py` | Отчёт о смещении pinned source; ничего не меняет |
| `scripts/validate_project_support.py` | Чтение манифеста capability для скриптов вне валидатора |
| `scripts/apply-capability-artifacts.py` | CLI плана и применения артефактов capability |
| `scripts/apply-capability-artifacts.sh` | Обёртка плана артефактов для macOS/Linux |
| `scripts/apply-capability-artifacts.ps1` | Обёртка плана артефактов для Windows |
| `scripts/validate-project.sh` | Validator wrapper для macOS/Linux |
| `scripts/validate-project.ps1` | Validator wrapper для Windows |
| `scripts/project-doctor.sh` | Environment + project doctor для macOS/Linux |
| `scripts/project-doctor.ps1` | Environment + project doctor для Windows |
| `scripts/test-validator.py` | Regression tests validator и exit codes |
| `scripts/promotion_candidates.py` | Генератор collision-resistant candidate ID и schema validator очереди |
| `scripts/test-promotion-candidates.py` | Regression tests candidate generator, duplicate guard и legacy ID |
| `scripts/compress-project.py` | Level-1 компрессия проекта (отчёт по умолчанию, `--apply` обратимое) |
| `scripts/compress-project.sh` | Compression wrapper для macOS/Linux |
| `scripts/compress-project.ps1` | Compression wrapper для Windows |
| `scripts/test-compress-project.py` | Regression tests компрессии (сплит, архив, cruft, idempotency) |
| `scripts/sync_global_agents.py` | Read-only parser и secret-safe global policy check/diff |
| `scripts/sync-global-agents.sh` | Global policy sync inspection для macOS/Linux |
| `scripts/sync-global-agents.ps1` | Global policy sync inspection для Windows |
| `scripts/test-agent-sync.py` | Regression tests managed-block states и отсутствия mutation |
| `scripts/project_metadata.py` | Общая schema validation и rendering project metadata |
| `scripts/plan_migration.py` | Fingerprint-защищённый migration planner/executor для project/global targets |
| `scripts/plan-migration.sh` | Migration planner wrapper для macOS/Linux |
| `scripts/plan-migration.ps1` | Migration planner wrapper для Windows |
| `scripts/test-migration-planner.py` | Regression tests manifests, blockers, previews и no-mutation |
| `scripts/test-artifacts-ledger.py` | Тесты контракта ledger managed-артефактов |
| `scripts/test-payload-classes.py` | Тесты доставки артефактов: подстановка против побайтного копирования |
| `scripts/test-capability-artifacts.py` | Тесты транзакционной установки и обновления артефактов capability |
| `scripts/test-preset-core.py` | Тесты раскрытия preset, инварианта ядра и parity обоих bootstrap |
| `scripts/test-release-manifest.py` | Тесты паспорта release, ledger артефактов и сборки |
| `scripts/test-one-c-scaffold.py` | Тесты каркаса 1С-проекта и схемы реестра баз |
| `scripts/test-1c-readiness.py` | Сверка матрицы готовности с планом и проверка её доказательств |
| `scripts/test-no-secrets.py` | Сканер: секреты, машинные пути и имена рабочих баз |
| `scripts/check-1c-component-links.py` | Report-only проверка внешних ссылок каталога компонентов |
| `scripts/one_c_source.py` | Контракт конвертации EDT ↔ XML: временный каталог, детерминизм, возврат в канон |
| `scripts/export-1c-source.py` | Выгрузка канона в XML и возврат изменений |
| `scripts/export-1c-source.sh` | POSIX-обёртка выгрузки исходников |
| `scripts/export-1c-source.ps1` | PowerShell-обёртка выгрузки исходников |
| `scripts/test-1c-source.py` | Тесты конвертации: расположение выгрузки, детерминизм, блокировка, возврат |
| `scripts/one_c_doctor.py` | Диагностика окружения 1С: allowlist источников, маскирование до вывода, статус и следствие в каждой строке |
| `scripts/test-1c-doctor.py` | Тесты диагностики: чтение вне allowlist отклоняется, значение секрета не доходит до отчёта |
| `scripts/one_c_session.py` | Session lock: какую базу сессии разрешено трогать и чем это подтверждено |
| `scripts/test-1c-session.py` | Тесты гейта: отказ без lock, без подтверждения production, при смене порта |
| `config/1c-components.tsv` | Каталог компонентов среды 1С: класс, назначение, последствия отказа, источник и способ установки |
| `scripts/one_c_components.py` | Загрузка каталога компонентов и prompt с обязательным набором полей |
| `scripts/one_c_setup.py` | Исполнитель настройки среды: план, установка только подтверждённого, фактическая перепроверка |
| `scripts/test-1c-setup.py` | Тесты каталога и настройки: полнота prompt, только подтверждённая установка, репозиторий не трогается |
| `scripts/one_c_provider.py` | Обнаружение внешнего MCP provider: identity, health, инструменты, запрет запуска контейнеров |
| `templates/new-project/capabilities/1c/PROJECT_1C.template.md` | Карточка базы: версия БСП, режим поддержки, снятия с поддержки, особенности |
| `scripts/test-1c-provider.py` | Тесты provider: переиспользование deployment, отказ на docker run, нерешённый endpoint |
| `scripts/one_c_yaxunit.py` | Разбор отчёта YAxUnit: провал, ошибка и пропуск различаются |
| `scripts/test-1c-yaxunit.py` | Тесты отчёта: прогон без отчёта — не пропуск, а отказ |
| `templates/new-project/capabilities/transcribe/` | Capability `transcribe`: локальная расшифровка, skill, скрипт и карточка проекта |
| `scripts/test-transcribe.py` | Тесты локальной расшифровки: пустой результат — отказ, кадры fail-closed, атомарная запись |
| `scripts/one_c_clients.py` | Контракт клиентских проекций 1С: владение, классы разрешений, транзакционная запись |
| `scripts/render-1c-clients.py` | Сборка клиентских проекций 1С из каталога ролей и реестра баз |
| `scripts/render-1c-clients.sh` | POSIX-обёртка сборки клиентских проекций |
| `scripts/render-1c-clients.ps1` | PowerShell-обёртка сборки клиентских проекций |
| `scripts/test-1c-clients.py` | Тесты клиентских проекций: владение, идемпотентность, классы разрешений |
| `scripts/standardize_existing_project.py` | Read-only decision report для стандартизации существующего проекта |
| `scripts/standardize-existing-project.sh` | Existing-project standardization planner для macOS/Linux |
| `scripts/standardize-existing-project.ps1` | Existing-project standardization planner для Windows |
| `scripts/test-standardize-existing-project.py` | Regression tests decision report и отсутствия mutation |
| `scripts/test-agent-setup.sh` | Smoke-тест global/scoped agent setup (macOS/Linux) |
| `scripts/test-agent-setup.ps1` | Smoke-тест global/scoped agent setup (Windows) |
| `scripts/test-skills.sh` | Контракт skills и правил: делегирует `check_skills.py` (macOS/Linux) |
| `scripts/test-skills.ps1` | Контракт skills и правил: делегирует `check_skills.py` (Windows) |
| `scripts/test-check-skills.py` | Юнит-тесты `check_skills.py` на временных фикстурах |
| `scripts/test-standard-metrics.py` | Проверка метрик стандарта: размеры документов и пороги компрессии |
| `scripts/test-powershell-syntax.ps1` | Проверка синтаксиса PowerShell с корректным кодом возврата |
| `scripts/test-powershell-environment.ps1` | Regression test изоляции HOME/Git environment между PowerShell suites |
| `scripts/check-action-pins.py` | Запрет mutable external Action references |
| `scripts/test-supply-chain.py` | Regression tests Action SHA/Docker digest policy |
| `scripts/best_practices_manifest.py` | Writer schema 2 preferences для Best Practices consumer manifest |
| `scripts/test-best-practices-contract.py` | Проверка контракта соседней базы Best Practices |
| `scripts/test-best-practices-manifest.py` | Regression tests consumer manifest writer |
| `scripts/test-best-practices-e2e.py` | Cross-repo E2E NPR writer ↔ pinned BP loader/report |
| `scripts/check_github_governance.py` | Read-only audit rulesets и единственного owner-admin |
| `scripts/test-github-governance.py` | Regression tests governance-инвариантов |
| `.github/dependabot.yml` | Еженедельные GitHub Actions updates |
| `.github/workflows/ci.yml` | CI: syntax-check и runtime-тесты на каждый push/PR |
| `.github/workflows/bp-pin-watch.yml` | Scheduled read-only detector drift reviewed Best Practices pin |
| `.github/workflows/macos-smoke.yml` | Path-triggered и ручной macOS smoke suite |
