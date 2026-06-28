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
4. `scripts/` создаёт новый проект/repo внутри общего vault из выбранного
   профиля.
5. `.agents/skills/` хранит канонические Agent Skills для Codex, а
   `.claude/skills/` — минимальные мосты Claude Code к тем же workflow.

Родительская рабочая папка является Obsidian vault. Каждый вложенный проект —
отдельный git-репозиторий без собственной `.obsidian`. Один набор Markdown-
файлов используется Obsidian и агентами (Codex, Claude Code) без копирования.

Машиночитаемые источники истины не преобразуются в ручные Markdown-копии.

Скиллы используют общий стандарт `SKILL.md`. Инструкции не копируются между
агентами: Claude-мост указывает на канонический skill в `.agents/skills/`.
Документация хранит назначение, связи, ограничения и эксплуатационный контекст.
