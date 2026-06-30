---
type: project
status: active
owner: mx
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[INDEX]]"
  - "[[README]]"
  - "[[docs/architecture/ARCHITECTURE|ARCHITECTURE]]"
  - "[[docs/research/PROJECT_ARTIFACT_MODEL|PROJECT_ARTIFACT_MODEL]]"
---

# Проект

## Цель

Хранить единый переносимый стандарт создания новых проектов для AI-агентов
(Codex, Claude Code и других AGENTS.md-совместимых), Obsidian и GitHub.

## Краткое техническое описание

Проект предназначен для того, чтобы новый репозиторий можно было создать не как
разовый набор файлов, а как повторяемый стандарт с проверяемой структурой,
едиными правилами для агентов и предсказуемой документацией.

На практике он:

- создаёт каркас нового проекта по профилю;
- задаёт единый источник правил через `AGENTS.md` и импорт в `CLAUDE.md`;
- поддерживает модель "одна папка проекта = git root = папка внутри общего
  Obsidian vault";
- валидирует структуру проекта и среду;
- помогает безопасно эволюционировать стандарт через versioned contracts и
  migration plans.

## Scope

- [[GLOBAL_AGENT_INSTRUCTIONS|глобальные инструкции агента]];
- проектный шаблон [[templates/new-project/AGENTS.template|AGENTS]];
- обязательные и условные Markdown-артефакты;
- bootstrap-скрипты для macOS/Linux и Windows;
- универсальные Agent Skills для настройки компьютера и создания проекта;
- правила переносимости, секретов и источников истины.
- версионируемый контракт профилей и policy invariants.
- read-only validator и doctor для project/environment diagnostics.
- read-only managed-block проверка глобальной policy без изменения active file.
- fingerprint-защищённый migration engine для legacy metadata и global marker adoption.
- immutable GitHub Actions policy, Dependabot, macOS smoke и supply-chain threat model.

## Non-goals

- автоматическая установка Obsidian, Git или GitHub CLI;
- перезапись существующего глобального `~/.codex/AGENTS.md`;
- хранение токенов, паролей и персональных путей компьютера;
- создание пустых документов без текущего назначения.

## Критерии успеха

- репозиторий клонируется на macOS и Windows;
- проект находится внутри общего Obsidian vault и не создаёт вложенный vault;
- bootstrap создаёт согласованную структуру нового проекта;
- новый проект не зависит от исходного компьютера;
- инструкции одинаково трактуют vault, repo и Markdown-файлы.

## Основные команды пользователя

- `./scripts/setup-global-agents.sh` или `.\scripts\setup-global-agents.ps1` — один раз настроить глобальные правила Codex/Claude.
- `./scripts/bootstrap-new-project.sh ...` или `.\scripts\bootstrap-new-project.ps1 ...` — создать новый проект.
- `./scripts/project-doctor.sh --root . --agent-mode codex` или `.\scripts\project-doctor.ps1 -Root . -AgentMode codex` — проверить среду и проект.
- `./scripts/validate-project.sh --root . --kind rules` или `.\scripts\validate-project.ps1 -Root . -Kind rules` — запустить read-only validator.
- `./scripts/sync-global-agents.sh --check` или `.\scripts\sync-global-agents.ps1 -Check` — проверить глобальные правила Codex/Claude.
- `./scripts/plan-migration.sh --plan ...` или `.\scripts\plan-migration.ps1 -Plan ...` — построить migration plan.
