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
| 2 | Cross-repo/governance аудит после структурного изменения | 2026-07-07 | Верификация NPR ↔ BP, GitHub governance | После структурного или многорепозиторного изменения не полагаться на локальный зелёный тест-цикл (он проверяет только свой репозиторий): прогнать broad read-only аудит — поиск в соседнем репозитории удалённых skills/маршрутов, `gh api` для branch protection и состояния веток/PR, сверка реализации с Consequences соответствующего ADR; результат записать в review/research и `DEFECTS`. | Два применения 2026-07-07: первоначальный аудит выявил дефекты 48–50 и findings P0/P2; closeout фазы 7 выявил stale BP pin и skill hash. Evidence: [[docs/research/PROJECT_AUDIT_2026-07]], [[docs/reviews/PHASE_7_CONSUMER_PILOT_REVIEW_2026-07-07]] и accepted BP practice `PC-2026-850607ffdb29`. |

---

### Entry format

Когда добавляете паттерн, скопируйте строку и заполните:

- **#** — последовательный номер, не переиспользовать.
- **Title** — короткое название повторяемой задачи или подхода.
- **Added** — дата в формате `YYYY-MM-DD`.
- **Component** — файл, модуль, подсистема или workflow, к которому относится паттерн.
- **Pattern** — конкретные проверенные шаги или правило, достаточно точные для повторения.
- **Evidence** — почему паттерну можно доверять: коммиты, PR, тесты или другая проверка.
