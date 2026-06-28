# Индекс

| Путь | Назначение |
|---|---|
| [[README|README.md]] | Использование набора на новом компьютере |
| [[OVERVIEW|OVERVIEW.md]] | Краткое описание набора для коллег |
| [[AGENTS|AGENTS.md]] | Правила агента для этого проекта |
| [[CLAUDE|CLAUDE.md]] | Imports [[AGENTS]] for Claude Code |
| [[GLOBAL_AGENT_INSTRUCTIONS|GLOBAL_AGENT_INSTRUCTIONS.md]] | Переносимый блок глобальных инструкций агента |
| [[PROJECT|PROJECT.md]] | Цели, scope, ограничения и критерии успеха |
| [[CHANGELOG|CHANGELOG.md]] | Заметные изменения набора правил |
| [[TOOLS|TOOLS.md]] | Установленные инструменты, версии и команды проверки |
| `requirements-dev.txt` | Python-зависимости для сопровождения Agent Skills |
| [[docs/README|docs/README.md]] | Индекс отдельной папки документации |
| [[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT.md]] | Создание проекта вручную или по запросу агенту |
| [[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER.md]] | Настройка нового macOS/Windows-компьютера |
| [[docs/architecture/ARCHITECTURE|ARCHITECTURE.md]] | Архитектура переносимого набора |
| [[docs/architecture/decisions/ADR-0001-two-level-documentation|ADR-0001]] | Решение о двухуровневой документации |
| [[docs/research/PROJECT_ARTIFACT_MODEL|PROJECT_ARTIFACT_MODEL.md]] | Обоснование структуры артефактов |
| [[docs/research/MUST_HAVE_PROJECT_TOOLING_2026|MUST_HAVE_PROJECT_TOOLING_2026.md]] | Исследование обязательной базы инструментов в 2026 году |
| [[docs/reviews/CODE_REVIEW_scripts_2026-06-28|CODE_REVIEW_scripts_2026-06-28.md]] | Ревью shell-, PowerShell-скриптов и CI |
| [[docs/quality/TESTING|TESTING.md]] | Матрица и команды проверки скриптов |
| [[docs/quality/DEFECTS|DEFECTS.md]] | Реестр обнаруженных и исправленных дефектов |
| [[TEMPLATES|TEMPLATES.md]] | Каталог и назначение всех шаблонов |
| [[.agents/skills/setup-new-computer/SKILL|setup-new-computer]] | Универсальный workflow настройки компьютера |
| [[.agents/skills/create-new-project/SKILL|create-new-project]] | Универсальный workflow создания проекта |
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
| `scripts/test-agent-setup.sh` | Smoke-тест global/scoped agent setup (macOS/Linux) |
| `scripts/test-agent-setup.ps1` | Smoke-тест global/scoped agent setup (Windows) |
| `scripts/test-skills.sh` | Проверка универсальных skills и Claude-мостов (macOS/Linux) |
| `scripts/test-skills.ps1` | Проверка универсальных skills и Claude-мостов (Windows) |
| `scripts/test-powershell-syntax.ps1` | Проверка синтаксиса PowerShell с корректным кодом возврата |
| `.github/workflows/ci.yml` | CI: syntax-check и runtime-тесты на каждый push/PR |
