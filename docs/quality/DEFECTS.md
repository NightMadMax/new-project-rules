---
type: defect-log
status: active
owner: project
last_verified: 2026-06-28
related:
  - "[[docs/README]]"
  - "[[docs/quality/TESTING]]"
---

# Дефекты

Обнаруженные дефекты не удаляются: после исправления запись переносится в
соответствующий раздел с датой и commit.

## Open

| # | Title | Discovered | Component | Description |
|---|---|---|---|---|
| — | | | | |

## Fixed

| # | Title | Discovered | Fixed | Commit | Root Cause |
|---|---|---|---|---|---|
| 1 | Mojibake в UI-метаданных skill | 2026-06-28 | 2026-06-28 | `a999788` | Native Windows исказил кириллические `--interface`; UI metadata переведены в ASCII. |
| 2 | Skill helpers требуют отсутствующий PyYAML | 2026-06-28 | 2026-06-28 | `a999788` | Runtime не содержал `PyYAML`; добавлен `requirements-dev.txt`, установлен и проверен `PyYAML 6.0.3`. |
| 3 | Skill helpers читают UTF-8 как cp1251 | 2026-06-28 | 2026-06-28 | `a999788` | `Path.read_text()` выбрал legacy code page; helpers запускаются с `PYTHONUTF8=1`, workaround записан в [[TOOLS]]. |

## Won't Fix

| # | Title | Discovered | Reason |
|---|---|---|---|
| 4 | POSIX symlink-тесты падают в Git Bash без symlink support | 2026-06-28 | Git Bash `ln -s` на этой Windows копирует файл, поэтому resolver-тесты получают неверный каталог. Windows поддерживается PowerShell-набором; POSIX symlink-сценарии выполняются в macOS/Linux и CI. |
