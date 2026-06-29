---
type: testing
status: active
owner: project
last_verified: 2026-06-29
source_of_truth: repository
related:
  - "[[INDEX]]"
  - "[[docs/reviews/CODE_REVIEW_scripts_2026-06-28]]"
---

# Проверка скриптов

## Поддерживаемые среды

| Среда | Проверка |
|---|---|
| macOS, системный `sh` | Локальная обязательная проверка перед публикацией |
| Ubuntu, `sh` | GitHub Actions |
| Windows PowerShell 5.1 | GitHub Actions |
| PowerShell 7 | Локально и в GitHub Actions |

Постоянный macOS runner не используется, поскольку репозиторий приватный. Риск
различий BSD/GNU закрывается локальным прогоном на macOS и отсутствием
GNU-специфичных флагов в shell-скриптах.

## Локальные команды

```sh
for file in scripts/*.sh; do sh -n "$file"; done
sh scripts/test-bootstrap.sh
sh scripts/test-contract.sh
sh scripts/test-agent-setup.sh
sh scripts/test-skills.sh
```

```powershell
.\scripts\test-powershell-syntax.ps1
.\scripts\test-bootstrap.ps1
.\scripts\test-contract.ps1
.\scripts\test-agent-setup.ps1
.\scripts\test-skills.ps1
```

PowerShell-проверки следует выполнять в Windows PowerShell 5.1 и PowerShell 7.
Parser-check обязан возвращать ненулевой код, если хотя бы один файл содержит
синтаксическую ошибку.

## Проверяемые сценарии

- создание всех bootstrap-профилей и точный состав файлов;
- parity фактических shell/PowerShell outputs с `config/profiles.tsv`;
- валидность `STANDARD_VERSION` и обязательных policy literals;
- полнота `docs/README.md` для расширенных профилей;
- валидность Agent Skills, совпадение Claude-мостов и канонических metadata;
- наличие обязательных Knowledge Promotion и Defect Tracking в переносимых
  global/project rules;
- начальный commit при настроенной Git-идентичности;
- staged-состояние без commit при отсутствующей идентичности;
- корректный отказ при ошибке `git init`, `git add`, `git status` или commit;
- rollback отсутствующего или изначально пустого destination при ошибке;
- shell-запуск напрямую, через `PATH` и символическую ссылку;
- создание, повторный запуск и конфликт global/scoped agent setup;
- отказ от scope path traversal до создания каталога;
- режимы environment check `codex`, `claude` и `both`;
- точные импорты `CLAUDE.md` и отсутствие дублей в `INDEX.md`;
- UTF-8 без BOM, отсутствие шаблонных плейсхолдеров и чистое git-дерево.
