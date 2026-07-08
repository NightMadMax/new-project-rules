---
type: code-review
status: complete
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/guides/CREATE_NEW_PROJECT]]"
  - "[[docs/architecture/BEST_PRACTICES_CONTRACT]]"
  - "[[docs/quality/DEFECTS]]"
---

# Code review A3: schema 2 consumer writer

## Scope

Проверены writer, create-new-project skill, переносимый project template,
пользовательские guides, CI и regression tests. Корневые `AGENTS.md` и
`CLAUDE.md` не изменялись в середине сессии.

## Findings и решения

1. Legacy writer смешивал предпочтение секции и факт применения. Контракт
   разделён: `preferences` хранит `ask`/`optout`, `practices` — outcomes.
2. Ручная JSON-запись могла перетереть outcomes. Writer строго загружает schema
   2 и сохраняет существующий `practices` без изменений.
3. Неявный upgrade schema 1 обходил бы review миграции. Writer блокирует schema
   1 и направляет к отдельному migration workflow Best Practices.
4. Запись через symlink могла выйти за project root. Symlink блокируется, запись
   выполняется через соседний temporary file и atomic replace.

## Verification

- новый global optout создаёт только canonical schema 2;
- section preference сохраняет practice outcomes;
- schema 1 и symlink отклоняются без mutation;
- CLI invalid preference не создаёт manifest;
- suite включён в Ubuntu, Windows и macOS CI.

## Verdict

A3 принята. Реальная совместимость writer с canonical BP loader проверяется
отдельным cross-repository E2E gate в A4.
