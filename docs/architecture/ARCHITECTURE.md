---
type: architecture
status: active
owner: project
last_verified: 2026-06-27
source_of_truth: repository
related:
  - "[[PROJECT]]"
  - "[[INDEX]]"
  - "[[docs/architecture/decisions/ADR-0001-two-level-documentation|ADR-0001]]"
  - "[[docs/research/PROJECT_ARTIFACT_MODEL|PROJECT_ARTIFACT_MODEL]]"
---

# Архитектура

Проект состоит из четырёх слоёв:

1. [[GLOBAL_AGENT_INSTRUCTIONS]] задаёт поведение агента до открытия проекта.
2. [[AGENTS]] задаёт локальные правила конкретного репозитория.
3. [[TEMPLATES]] описывает переиспользуемые артефакты.
4. `scripts/` создаёт новый vault/repo из выбранного профиля.

Новый проект не создаёт отдельную копию Markdown для Obsidian. Одна папка и
один набор файлов используются Obsidian, git и агентами (Codex, Claude Code)
одновременно.

Машиночитаемые источники истины не преобразуются в ручные Markdown-копии.
Документация хранит назначение, связи, ограничения и эксплуатационный контекст.
