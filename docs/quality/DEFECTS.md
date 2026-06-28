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
| 1 | Mojibake в UI-метаданных skill | 2026-06-28 | `skill-creator/init_skill.py` | Передача кириллических `--interface` через native Windows PowerShell создала повреждённый `agents/openai.yaml`. Root cause: несовпадение кодировки аргументов процесса; исправление в проекте — ASCII UI-метаданные. |
| 2 | Skill helpers требуют отсутствующий PyYAML | 2026-06-28 | `skill-creator/scripts` | `generate_openai_yaml.py` и `quick_validate.py` завершаются `ModuleNotFoundError: No module named 'yaml'`. Внешние helpers не обеспечивают runtime-зависимость; проект использует проверенный UTF-8 YAML и dependency-free smoke-тесты без установки нового пакета. |
| 3 | Skill helpers читают UTF-8 как cp1251 | 2026-06-28 | `skill-creator/scripts` | На Windows `generate_openai_yaml.py` завершился `UnicodeDecodeError`, потому что `Path.read_text()` использовал системную encoding. Workaround: запускать helpers с `PYTHONUTF8=1`. |

## Fixed

| # | Title | Discovered | Fixed | Commit | Root Cause |
|---|---|---|---|---|---|
| — | | | | | |

## Won't Fix

| # | Title | Discovered | Reason |
|---|---|---|---|
| 4 | POSIX symlink-тесты падают в Git Bash без symlink support | 2026-06-28 | Git Bash `ln -s` на этой Windows копирует файл, поэтому resolver-тесты получают неверный каталог. Windows поддерживается PowerShell-набором; POSIX symlink-сценарии выполняются в macOS/Linux и CI. |
