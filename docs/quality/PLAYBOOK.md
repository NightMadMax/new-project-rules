---
type: playbook
status: active
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/README]]"
  - "[[docs/quality/DEFECTS]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY]]"
---

# Playbook

Проверенные, повторяемые удачные паттерны работы в этом проекте. Это
позитивная пара к журналу дефектов: если `DEFECTS` фиксирует, что ломалось и
почему, то `PLAYBOOK` фиксирует, какой способ уже доказал свою правильность и
должен повторяться без повторного изобретения.

Держите записи проектно-специфичными. Если паттерн применим к нескольким
независимым проектам и очищен от приватного контекста, его нужно не оставлять
только здесь, а предлагать кандидатом в соседнюю базу Best Practices.

## Patterns

| # | Title | Added | Component | Pattern | Evidence |
|---|---|---|---|---|---|
| 1 | Refresh глобальной managed policy при `managed_drift` | 2026-07-03 | `~/.codex/AGENTS.md`, `scripts/sync_global_agents.py` | Migration engine намеренно блокирует `managed_drift`; обновлять managed block ручным шагом по паттерну engine: timestamped backup рядом с активным файлом, desired text через `sync_global_agents.desired_text(state)` (сохраняет пользовательский prefix/suffix), запись через `plan_migration.atomic_write`, postcondition `sync-global-agents --check` → `managed_match`, запись в [[ACTIONS]] с SHA-256 и rollback. | Два успешных применения: 2026-07-02 (второй компьютер, дефект 28) и 2026-07-03 (пакет B); записи в [[ACTIONS]]. |
| 3 | Regression-тест проверять откатом фикса, а не зелёным прогоном | 2026-07-16 | `scripts/test-*.py`, любой фикс дефекта | Зелёный новый тест ничего не доказывает: он может проходить и на багованном коде, тогда дефект остаётся незакрытым. Перед commit прогнать новые тесты на откаченном коде и убедиться, что падает именно тест дефекта: `cp scripts/<file>.py /tmp/fixed.py && git checkout scripts/<file>.py && python scripts/test-<suite>.py <TestCase>.<test>` (ожидается FAIL), затем `cp /tmp/fixed.py scripts/<file>.py`. Guard-тесты (что фикс не ослабил проверку) обязаны проходить на обеих версиях. | Два применения 2026-07-16: проверка откатом показала, что тест дефекта №69 проходит на старом коде — баг маскировался basename-fallback, тест был переписан на неоднозначный stem и только тогда стал падать; та же проверка подтвердила тест дефекта №71 (падает без `metadata_profile_for`). Evidence: commit `a210e02`, [[docs/quality/DEFECTS\|дефекты]] №69–71. |
| 2 | Cross-repo/governance аудит после структурного изменения | 2026-07-07 | Верификация NPR ↔ BP, GitHub governance | После структурного или многорепозиторного изменения не полагаться на локальный зелёный тест-цикл (он проверяет только свой репозиторий): прогнать broad read-only аудит — поиск в соседнем репозитории удалённых skills/маршрутов, `gh api` для branch protection и состояния веток/PR, сверка реализации с Consequences соответствующего ADR; результат записать в review/research и `DEFECTS`. | Два применения 2026-07-07: первоначальный аудит выявил дефекты 48–50 и findings P0/P2; closeout фазы 7 выявил stale BP pin и skill hash. Evidence: [[docs/research/archive/PROJECT_AUDIT_2026-07]], [[docs/reviews/archive/PHASE_7_CONSUMER_PILOT_REVIEW_2026-07-07]] и accepted BP practice `PC-2026-850607ffdb29`. |

---

### Entry format

Когда добавляете паттерн, скопируйте строку и заполните:

- **#** — последовательный номер, не переиспользовать.
- **Title** — короткое название повторяемой задачи или подхода.
- **Added** — дата в формате `YYYY-MM-DD`.
- **Component** — файл, модуль, подсистема или workflow, к которому относится паттерн.
- **Pattern** — конкретные проверенные шаги или правило, достаточно точные для повторения.
- **Evidence** — почему паттерну можно доверять: коммиты, PR, тесты или другая проверка.
