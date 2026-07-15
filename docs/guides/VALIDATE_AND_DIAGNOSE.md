---
type: guide
status: active
owner: project
last_verified: 2026-06-29
source_of_truth: repository
related:
  - "[[docs/quality/TESTING]]"
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN]]"
  - "[[docs/architecture/decisions/ADR-0002-versioned-project-contract]]"
  - "[[docs/guides/SETUP_NEW_COMPUTER]]"
---

# Валидация проекта и диагностика компьютера

Validator и doctor работают только на чтение и не исправляют файлы.

| Команда | Отвечает на вопрос | Проверяет |
|---|---|---|
| Validator | Соответствует ли репозиторий стандарту? | файлы, профиль, индексы, links, frontmatter, placeholders и safety patterns |
| Doctor | Почему workflow не работает на этом компьютере? | environment check, validator, Git state, remote и Obsidian placement |

## Требования

Validator использует Python 3.9+ standard library без внешних packages. Базовый
doctor запускает environment check и без Python, но явно помечает structural
validation как пропущенную. Скрипты ничего не устанавливают автоматически.

## Validator

macOS/Linux:

```sh
./scripts/validate-project.sh --root . --kind rules
./scripts/validate-project.sh --root "/path/to/project" --kind project --profile software
```

Windows:

```powershell
.\scripts\validate-project.ps1 -Root . -Kind rules
.\scripts\validate-project.ps1 -Root "C:\path\to\project" -Kind project -Profile software
```

`--kind auto` определяет rules repository по `STANDARD_VERSION` и
`config/profiles.tsv`. Для legacy project без `.project-standard.json` profile
выводится только при точном совпадении известных managed artifacts. При
неоднозначности нужно передать profile явно; validator не угадывает его по
частичному дереву.

Проверяются:

- required core и artifacts выбранного профиля;
- точный `CLAUDE.md=@AGENTS.md`;
- связи в `INDEX.md` и `docs/README.md`;
- wikilinks и frontmatter schema;
- template placeholders;
- nested `.obsidian` и raw agent memory;
- high-confidence secret patterns;
- machine-specific absolute paths;
- существующая `.project-standard.json`, если она уже есть.

Проверяются только файлы самого проекта. Набор берётся из
`git ls-files --cached --others --exclude-standard`, поэтому всё, что исключает
`.gitignore` (`node_modules/`, `dist/`, build output), не читается и не может
дать findings. Если git недоступен или root не является repository, validator
обходит дерево напрямую и пропускает только известные каталоги зависимостей —
в этом режиме чужие файлы вне списка могут попасть в отчёт.

Exit codes:

- `0` — validation errors отсутствуют;
- `1` — проект проверен, но найдены errors;
- `2` — неверный вызов или повреждён contract;
- `--report-only` — показать тот же отчёт, но вернуть `0`.

Warnings не меняют exit code. Auto-fix отсутствует намеренно.

## Doctor

macOS/Linux:

```sh
./scripts/project-doctor.sh --root . --agent-mode codex
```

Windows:

```powershell
.\scripts\project-doctor.ps1 -Root . -AgentMode codex
```

Doctor объединяет:

- наличие Git, `gh`, выбранных agents и Python;
- GitHub authentication и credential helper;
- validator report;
- git working tree и `origin`;
- поиск родительского Obsidian vault;
- обнаружение nested project vault.

Для сбора диагностического отчёта без блокирующего exit code используйте
`--report-only` или `-ReportOnly`. Этот режим не скрывает findings — меняется
только код возврата.
