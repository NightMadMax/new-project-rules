---
type: documentation-index
status: active
owner: project
last_verified: 2026-07-03
source_of_truth: repository
related:
  - "[[INDEX]]"
  - "[[README]]"
---

# Документация

## Руководства

- [[docs/guides/USE_THIS_PROJECT|Как работать с этим проектом]]
- [[docs/guides/MANUAL_SCRIPTS|Ручной запуск скриптов]]
- [[docs/guides/CREATE_NEW_PROJECT|Создание нового проекта]]
- [[docs/guides/ASSESS_EXISTING_PROJECT|Оценка существующего проекта]]
- [[docs/guides/STANDARDIZE_EXISTING_PROJECT|Стандартизация существующего проекта]]
- [[docs/guides/SETUP_NEW_COMPUTER|Подключение нового компьютера]]
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Перенос знаний между проектами]]
- [[docs/guides/VALIDATE_AND_DIAGNOSE|Валидация проекта и диагностика компьютера]]
- [[docs/guides/COMPRESS_PROJECT|Компрессия накопившегося «мусора» проекта]]
- [[docs/guides/SYNC_GLOBAL_AGENTS|Read-only синхронизация глобальных правил]]
- [[docs/guides/PLAN_MIGRATIONS|Планирование миграций без изменения файлов]]

## Архитектура и решения

- [[docs/architecture/ARCHITECTURE|Архитектура набора правил]]
- [[docs/architecture/decisions/ADR-0001-two-level-documentation|ADR-0001: двухуровневая документация]]
- [[docs/architecture/decisions/ADR-0002-versioned-project-contract|ADR-0002: версионируемый контракт проекта]]
- [[docs/architecture/PROJECT_STANDARD_SCHEMA|Schema project standard metadata]]

## Исследования

- [[docs/research/PROJECT_ARTIFACT_MODEL|Модель артефактов проекта]]
- [[docs/research/MUST_HAVE_PROJECT_TOOLING_2026|Обязательная база инструментов проекта в 2026 году]]
- [[docs/research/STRATEGIC_EVOLUTION_PLAN|Стратегический план развития policy-системы]]
- [[docs/research/AGENT_RUNTIME_CAPABILITIES_2026|Рантайм-возможности Codex/Claude Code 2026]]
- [[docs/research/AGENT_COMMUNITY_PRACTICES_2026|Community-практики Claude Code/Codex]]
- [[docs/research/PROJECT_AUDIT_2026-07|Аудит проекта и направления улучшений — июль 2026]]
- [[docs/research/PROJECT_AUDIT_2026-07-03|Повторный глубокий аудит проекта — 2026-07-03]]
- [[docs/research/BEST_PRACTICES_INTEGRATION|Интеграция базы Best Practices в создание проекта]]
- [[docs/research/PROJECT_COMPRESSION_PLAN|План: компрессия проекта (script + skill)]]
- [[docs/research/PROJECT_HARVEST_2026-07-06|Полный harvest соседних проектов — 2026-07-06]]

## Качество и ревью

- [[docs/quality/TESTING|Проверка скриптов]]
- [[docs/quality/DEFECTS|Реестр дефектов]]
- [[docs/quality/DEFECTS_ARCHIVE|Архив дефектов]]
- [[docs/quality/PLAYBOOK|Реестр проверенных удачных паттернов]]
- [[docs/quality/PROMOTION_CANDIDATES|Очередь кандидатов на knowledge promotion]]
- [[docs/quality/promotion-candidates/README|Файлы promotion candidates и генератор ID]]
- [[docs/reviews/CODE_REVIEW_scripts_2026-06-28|Ревью скриптов от 2026-06-28]]

## Безопасность

- [[docs/security/THREAT_MODEL|Threat model bootstrap и CI supply chain]]

## Стандартная структура нового проекта

```text
docs/
├── README.md
├── architecture/
│   └── decisions/
├── guides/
├── research/
├── reviews/       # при наличии code review
├── operations/    # для эксплуатируемых систем
├── quality/       # для проектов с кодом
├── api/           # при наличии API
├── data/          # при наличии постоянных данных
└── security/      # при наличии security-артефактов
```

Каталоги создаются только при необходимости. В корне проекта остаются входные
файлы `README.md`, `AGENTS.md`, `CLAUDE.md`, `INDEX.md`, `PROJECT.md` и
условный `CHANGELOG.md`.
