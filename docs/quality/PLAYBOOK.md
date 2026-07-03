---
type: playbook
status: active
owner: project
last_verified: 2026-07-03
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
только здесь, а предлагать к promotion в общий стандарт.

## Patterns

| # | Title | Added | Component | Pattern | Evidence |
|---|---|---|---|---|---|
| 1 | Refresh глобальной managed policy при `managed_drift` | 2026-07-03 | `~/.codex/AGENTS.md`, `scripts/sync_global_agents.py` | Migration engine намеренно блокирует `managed_drift`; обновлять managed block ручным шагом по паттерну engine: timestamped backup рядом с активным файлом, desired text через `sync_global_agents.desired_text(state)` (сохраняет пользовательский prefix/suffix), запись через `plan_migration.atomic_write`, postcondition `sync-global-agents --check` → `managed_match`, запись в [[ACTIONS]] с SHA-256 и rollback. | Два успешных применения: 2026-07-02 (второй компьютер, дефект 28) и 2026-07-03 (пакет B); записи в [[ACTIONS]]. |

---

### Entry format

Когда добавляете паттерн, скопируйте строку и заполните:

- **#** — последовательный номер, не переиспользовать.
- **Title** — короткое название повторяемой задачи или подхода.
- **Added** — дата в формате `YYYY-MM-DD`.
- **Component** — файл, модуль, подсистема или workflow, к которому относится паттерн.
- **Pattern** — конкретные проверенные шаги или правило, достаточно точные для повторения.
- **Evidence** — почему паттерну можно доверять: коммиты, PR, тесты или другая проверка.
