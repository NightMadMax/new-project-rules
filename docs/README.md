---
type: documentation-index
status: active
owner: project
last_verified: 2026-06-29
source_of_truth: repository
related:
  - "[[INDEX]]"
  - "[[README]]"
---

# Документация

## Руководства

- [[docs/guides/CREATE_NEW_PROJECT|Создание нового проекта]]
- [[docs/guides/SETUP_NEW_COMPUTER|Подключение нового компьютера]]
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Перенос знаний между проектами]]

## Архитектура и решения

- [[docs/architecture/ARCHITECTURE|Архитектура набора правил]]
- [[docs/architecture/decisions/ADR-0001-two-level-documentation|ADR-0001: двухуровневая документация]]

## Исследования

- [[docs/research/PROJECT_ARTIFACT_MODEL|Модель артефактов проекта]]
- [[docs/research/MUST_HAVE_PROJECT_TOOLING_2026|Обязательная база инструментов проекта в 2026 году]]
- [[docs/research/STRATEGIC_EVOLUTION_PLAN|Стратегический план развития policy-системы]]

## Качество и ревью

- [[docs/quality/TESTING|Проверка скриптов]]
- [[docs/quality/DEFECTS|Реестр дефектов]]
- [[docs/reviews/CODE_REVIEW_scripts_2026-06-28|Ревью скриптов от 2026-06-28]]

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
