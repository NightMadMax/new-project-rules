---
type: guide
status: active
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[GLOBAL_AGENT_INSTRUCTIONS]]"
  - "[[docs/guides/SETUP_NEW_COMPUTER]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN]]"
---

# Read-only синхронизация глобальных правил

Инструмент сравнивает переносимую политику из
[[GLOBAL_AGENT_INSTRUCTIONS]] с `~/.codex/AGENTS.md`. `sync-global-agents`
остаётся read-only; подтверждаемую запись выполняет отдельный migration engine
по [[docs/guides/PLAN_MIGRATIONS|reviewed fingerprint-плану]].

## Managed block

Управляемая область ограничена единственной парой markers:

```text
<!-- new-project-rules:begin schema=2 -->
...portable policy...
<!-- new-project-rules:end -->
```

Текст до и после блока остаётся пользовательским. Parser отклоняет
дублированные, переставленные, незакрытые markers и неизвестную schema.

## Состояния

| Состояние | Значение |
|---|---|
| `missing` | Active file отсутствует |
| `legacy_exact` | Весь active file совпадает с portable policy, но markers отсутствуют |
| `unmanaged_conflict` | Файл без markers содержит собственные правила; managed block дописывается ниже них подтверждаемой миграцией |
| `managed_match` | Managed block совпадает, внешний текст сохраняется |
| `managed_drift` | Managed block отличается от portable policy |
| `malformed` | Marker grammar повреждена или неоднозначна |
| `unsupported_schema` | Marker использует неподдерживаемую schema |

## Команды

macOS/Linux:

```sh
./scripts/sync-global-agents.sh --check
./scripts/sync-global-agents.sh --diff --report-only
```

Windows PowerShell:

```powershell
.\scripts\sync-global-agents.ps1 -Check
.\scripts\sync-global-agents.ps1 -Diff -ReportOnly
```

`--check` возвращает `0` только для `managed_match`, `1` для обнаруженного
расхождения или немигрированного состояния и `2` для ошибки usage/config.
`--report-only` всегда возвращает `0`, сохраняя findings в отчёте для CI и
doctor.

## Безопасность вывода

`--diff` не печатает содержимое active file. План содержит только состояние,
диапазоны строк, число строк и SHA-256 исходного/ожидаемого блока. Поэтому
случайная локальная инструкция или секрет не попадает в terminal и CI logs.

До migration переходное состояние — `legacy_exact`: содержимое уже правильное,
но markers добавляются только отдельной подтверждаемой миграцией с preview и
backup. На основном компьютере adoption выполнен 2026-06-30 и зафиксирован в
[[ACTIONS]]; ожидаемый state теперь `managed_match`. Read-only команды не
меняют ни `~/.codex/AGENTS.md`, ни `~/.claude/CLAUDE.md`.
