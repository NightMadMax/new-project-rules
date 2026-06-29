---
type: defect-log
status: active
owner: project
last_verified: 2026-06-29
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
| 5 | Переносимые правила расходятся с активными | 2026-06-29 | 2026-06-29 | `8a669b6` | Атомарное обновление global/project/template rules не было проверено semantic contract test. |
| 6 | Skill-тесты не запускаются в CI | 2026-06-29 | 2026-06-29 | `8a669b6` | Workflow не вызывал существующие `test-skills.*`. |
| 11 | Архитектура заявляет четыре слоя и перечисляет пять | 2026-06-29 | 2026-06-29 | `8a669b6` | Число слоёв не обновили после добавления Agent Skills. |
| 12 | Defect template создаёт фиктивный открытый дефект | 2026-06-29 | 2026-06-29 | `8a669b6` | Пример был помещён в рабочую таблицу вместо инструкции под ней. |
| 7 | Расширенные профили создают неполный docs index | 2026-06-29 | 2026-06-29 | `114788c` | Bootstrap обновлял только корневой `INDEX.md`, но не профильные разделы `docs/README.md`. |
| 8 | Claude одновременно optional и required | 2026-06-29 | 2026-06-29 | `114788c` | Environment check не различал agent mode и всегда требовал оба CLI. |
| 9 | Scoped setup создаёт внешний каталог до проверки | 2026-06-29 | 2026-06-29 | `114788c` | Scope path окончательно проверялся только после `mkdir` / `New-Item`. |
| 10 | Bootstrap не откатывает частично созданный проект | 2026-06-29 | 2026-06-29 | `114788c` | Генерация выполнялась прямо в destination без failure cleanup. |

## Won't Fix

| # | Title | Discovered | Reason |
|---|---|---|---|
| 4 | POSIX symlink-тесты падают в Git Bash без symlink support | 2026-06-28 | Git Bash `ln -s` на этой Windows копирует файл, поэтому resolver-тесты получают неверный каталог. Windows поддерживается PowerShell-набором; POSIX symlink-сценарии выполняются в macOS/Linux и CI. |
