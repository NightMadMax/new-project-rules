---
type: project
status: active
owner: mx
last_verified: 2026-06-29
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

## Scope

- [[GLOBAL_AGENT_INSTRUCTIONS|глобальные инструкции агента]];
- проектный шаблон [[templates/new-project/AGENTS.template|AGENTS]];
- обязательные и условные Markdown-артефакты;
- bootstrap-скрипты для macOS/Linux и Windows;
- универсальные Agent Skills для настройки компьютера и создания проекта;
- правила переносимости, секретов и источников истины.
- версионируемый контракт профилей и policy invariants.

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
