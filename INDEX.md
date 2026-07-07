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
| `config/policy-contract.tsv` | Обязательные policy literals в переносимых правилах |
| `config/migrations.tsv` | Migration IDs, targets, schema transitions и handlers |
| `config/standard-source.txt` | Канонический owner/repository без credentials и локальных путей |
| [[CHANGELOG|CHANGELOG.md]] | Заметные изменения набора правил |
| [[CHANGELOG_ARCHIVE|CHANGELOG_ARCHIVE.md]] | Архив старых релизов, перенесённых при компрессии |
| [[TOOLS|TOOLS.md]] | Установленные инструменты, версии и команды проверки |
| `requirements-dev.txt` | Python-зависимости для сопровождения Agent Skills |
| [[docs/README|docs/README.md]] | Индекс отдельной папки документации |
| [[docs/guides/USER_GUIDE|USER_GUIDE.md]] | Основное пользовательское руководство: установка, ежедневные сценарии и безопасные запросы агенту |
| [[docs/guides/USE_THIS_PROJECT|USE_THIS_PROJECT.md]] | Пользовательский вход: как работать с проектом и какими фразами ставить задачи агенту |
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
| [[docs/architecture/decisions/ADR-0001-two-level-documentation|ADR-0001]] | Решение о двухуровневой документации |
| [[docs/architecture/decisions/ADR-0002-versioned-project-contract|ADR-0002]] | Решение о TSV contract и hybrid runtime |
| [[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture|ADR-0003]] | Двухъярусная архитектура знаний: роли, маршрутизация, managed/unmanaged, судьба скиллов |
| [[docs/research/PROJECT_ARTIFACT_MODEL|PROJECT_ARTIFACT_MODEL.md]] | Обоснование структуры артефактов |
| [[docs/research/MUST_HAVE_PROJECT_TOOLING_2026|MUST_HAVE_PROJECT_TOOLING_2026.md]] | Исследование обязательной базы инструментов в 2026 году |
| [[docs/research/STRATEGIC_EVOLUTION_PLAN|STRATEGIC_EVOLUTION_PLAN.md]] | Реализованный план policy-системы и следующий продуктовый этап |
| [[docs/research/AGENT_RUNTIME_CAPABILITIES_2026|AGENT_RUNTIME_CAPABILITIES_2026.md]] | Рантайм-возможности Codex/Claude Code и план улучшений правил |
| [[docs/research/AGENT_COMMUNITY_PRACTICES_2026|AGENT_COMMUNITY_PRACTICES_2026.md]] | Community-практики Claude Code/Codex и кандидаты на внедрение |
| [[docs/research/PROJECT_AUDIT_2026-07|PROJECT_AUDIT_2026-07.md]] | Аудит проекта июль 2026: консистентность, обновления Codex/Claude Code, рекомендации |
| [[docs/research/PROJECT_AUDIT_2026-07-03|PROJECT_AUDIT_2026-07-03.md]] | Повторный глубокий аудит: adversarial standardization checks, CI, portability и readiness |
| [[docs/research/BEST_PRACTICES_INTEGRATION|BEST_PRACTICES_INTEGRATION.md]] | Решения по интеграции базы Best Practices в create-new-project |
| [[docs/research/PROJECT_HARVEST_2026-07-06|PROJECT_HARVEST_2026-07-06.md]] | Полный harvest checked-in lessons из соседних git-проектов |
| [[docs/research/NPR_BP_KNOWLEDGE_ARCHITECTURE_2026-07-06|NPR_BP_KNOWLEDGE_ARCHITECTURE_2026-07-06.md]] | Архитектура знаний между new-project-rules и Best Practices: дублирование, маршрутизация, SSOT |
| [[docs/research/NPR_BP_HARVEST_ANALYSIS_2026-07-07|NPR_BP_HARVEST_ANALYSIS_2026-07-07.md]] | Совместный функциональный harvest-анализ NPR и Best Practices: зрелость, GitHub-state, разрывы и приоритеты |
| [[docs/research/NPR_BP_REMEDIATION_PLAN_2026-07-07|NPR_BP_REMEDIATION_PLAN_2026-07-07.md]] | Поэтапный план исправления связки NPR и Best Practices с gates, проверками и Definition of Done |
| [[docs/reviews/CODE_REVIEW_scripts_2026-06-28|CODE_REVIEW_scripts_2026-06-28.md]] | Ревью shell-, PowerShell-скриптов и CI |
| [[docs/reviews/PHASE_2_MAIN_PROTECTION_REVIEW_2026-07-07|PHASE_2_MAIN_PROTECTION_REVIEW_2026-07-07.md]] | Финальный review GitHub ruleset и CODEOWNERS для защиты NPR main |
| [[docs/reviews/PHASE_4_CROSS_REPO_CONTRACT_REVIEW_2026-07-07|PHASE_4_CROSS_REPO_CONTRACT_REVIEW_2026-07-07.md]] | Финальный review pinned cross-repo contract NPR ↔ Best Practices |
| [[docs/reviews/PHASE_5_SEQUENTIAL_MIGRATIONS_REVIEW_2026-07-07|PHASE_5_SEQUENTIAL_MIGRATIONS_REVIEW_2026-07-07.md]] | Review schema 2 и последовательного migration graph |
| [[docs/reviews/A3_SCHEMA2_CONSUMER_WRITER_REVIEW_2026-07-07|A3_SCHEMA2_CONSUMER_WRITER_REVIEW_2026-07-07.md]] | Code review schema 2 writer для consumer preferences |
| [[docs/reviews/A4_CROSS_REPO_CONSUMER_E2E_REVIEW_2026-07-07|A4_CROSS_REPO_CONSUMER_E2E_REVIEW_2026-07-07.md]] | Code review исполняемого NPR ↔ BP consumer gate |
| [[docs/reviews/A5_NPR_CONSUMER_MANIFEST_MIGRATION_REVIEW_2026-07-07|A5_NPR_CONSUMER_MANIFEST_MIGRATION_REVIEW_2026-07-07.md]] | Review фактической миграции NPR consumer manifest |
| [[docs/quality/TESTING|TESTING.md]] | Матрица и команды проверки скриптов |
| [[docs/quality/DEFECTS|DEFECTS.md]] | Реестр обнаруженных и исправленных дефектов |
| [[docs/quality/DEFECTS_ARCHIVE|DEFECTS_ARCHIVE.md]] | Архив консолидированных Fixed-записей журнала дефектов |
| [[docs/quality/PLAYBOOK|PLAYBOOK.md]] | Реестр проверенных удачных паттернов и повторяемых good practices |
| [[docs/quality/PROMOTION_CANDIDATES|PROMOTION_CANDIDATES.md]] | Maintainer-only очередь затвердевания практик Best Practices в правила NPR |
| [[docs/quality/promotion-candidates/README|promotion-candidates/]] | Канонический one-file-per-candidate backlog и команды генератора |
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
| `scripts/bootstrap-new-project.sh` | Создание проекта на macOS/Linux |
| `scripts/bootstrap-new-project.ps1` | Создание проекта в Windows PowerShell |
| `scripts/setup-global-agents.sh` | Глобальная настройка Codex+Claude (macOS/Linux) |
| `scripts/setup-global-agents.ps1` | Глобальная настройка Codex+Claude (Windows) |
| `scripts/add-agent-scope.sh` | Правила для подкаталога (macOS/Linux) |
| `scripts/add-agent-scope.ps1` | Правила для подкаталога (Windows) |
| `scripts/check-environment.sh` | Проверка обязательной базы инструментов (macOS/Linux) |
| `scripts/check-environment.ps1` | Проверка обязательной базы инструментов (Windows) |
| `scripts/test-bootstrap.sh` | Регрессионный тест bootstrap (macOS/Linux) |
| `scripts/test-bootstrap.ps1` | Регрессионный тест bootstrap (Windows) |
| `scripts/test-contract.sh` | Parity contract и bootstrap outputs (macOS/Linux) |
| `scripts/test-contract.ps1` | Parity contract и bootstrap outputs (Windows) |
| `scripts/validate-project.py` | Общая read-only validation logic на Python 3.9+ |
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
| `scripts/standardize_existing_project.py` | Read-only decision report для стандартизации существующего проекта |
| `scripts/standardize-existing-project.sh` | Existing-project standardization planner для macOS/Linux |
| `scripts/standardize-existing-project.ps1` | Existing-project standardization planner для Windows |
| `scripts/test-standardize-existing-project.py` | Regression tests decision report и отсутствия mutation |
| `scripts/test-agent-setup.sh` | Smoke-тест global/scoped agent setup (macOS/Linux) |
| `scripts/test-agent-setup.ps1` | Smoke-тест global/scoped agent setup (Windows) |
| `scripts/test-skills.sh` | Проверка универсальных skills и Claude-мостов (macOS/Linux) |
| `scripts/test-skills.ps1` | Проверка универсальных skills и Claude-мостов (Windows) |
| `scripts/test-powershell-syntax.ps1` | Проверка синтаксиса PowerShell с корректным кодом возврата |
| `scripts/test-powershell-environment.ps1` | Regression test изоляции HOME/Git environment между PowerShell suites |
| `scripts/check-action-pins.py` | Запрет mutable external Action references |
| `scripts/test-supply-chain.py` | Regression tests Action SHA/Docker digest policy |
| `scripts/best_practices_manifest.py` | Writer schema 2 preferences для Best Practices consumer manifest |
| `scripts/test-best-practices-manifest.py` | Regression tests consumer manifest writer |
| `scripts/test-best-practices-e2e.py` | Cross-repo E2E NPR writer ↔ pinned BP loader/report |
| `.github/dependabot.yml` | Еженедельные GitHub Actions updates |
| `.github/workflows/ci.yml` | CI: syntax-check и runtime-тесты на каждый push/PR |
| `.github/workflows/macos-smoke.yml` | Path-triggered и ручной macOS smoke suite |
