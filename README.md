# Правила для нового проекта

Переносимый набор правил и шаблонов для создания проектов, в которых одна и та
же папка одновременно является:

- Obsidian vault;
- корнем git-репозитория;
- локальной копией отдельного GitHub-репозитория.

Markdown редактируется напрямую в папке проекта. REST API, helper,
синхронизация и вторая копия заметок не требуются.

## Руководства

- [[docs/README|Документация проекта]]
- [[docs/guides/CREATE_NEW_PROJECT|Как создать новый проект]]
- [[docs/guides/SETUP_NEW_COMPUTER|Как подключить новый компьютер]]

## Использование на другом компьютере

1. Клонировать этот репозиторий.
2. Открыть клонированную папку в Obsidian через **Open folder as vault**.
3. Перенести содержимое [[GLOBAL_AGENT_INSTRUCTIONS|глобальных инструкций]] в глобальный
   `~/.codex/AGENTS.md`, сохранив уже существующие инструкции этого компьютера.
4. Настроить глобальные правила для Claude Code (один раз на компьютер) —
   через импорт, без symlink. Скрипт создаёт `~/.claude/CLAUDE.md` с
   `@~/.codex/AGENTS.md`, не перезаписывает существующие инструкции и безопасен
   при повторном запуске:

   ```sh
   ./scripts/setup-global-agents.sh
   ```

   ```powershell
   .\scripts\setup-global-agents.ps1
   ```

   После настройки открыть Claude Code и выполнить `/memory`: список должен
   показывать глобальный `~/.claude/CLAUDE.md` и импортированные инструкции.
5. Для нового проекта запустить один из bootstrap-скриптов.

Навигация по vault: [[INDEX|индекс]], [[PROJECT|описание проекта]],
[[TEMPLATES|каталог шаблонов]].

macOS/Linux:

```sh
./scripts/bootstrap-new-project.sh "/path/to/New Project" "New Project" software
```

Windows PowerShell:

```powershell
.\scripts\bootstrap-new-project.ps1 -Destination "C:\Projects\New Project" -ProjectName "New Project" -Profile software
```

Профили:

- `minimal` — обязательное ядро документации;
- `software` — ядро, архитектура, ADR, исследования, ревью и тестирование;
- `operated` — software плюс окружения, runbook, инциденты и внешние действия;
- `all` — все доступные шаблоны, включая API, данные и безопасность.

Bootstrap создаёт в каждом проекте `CLAUDE.md` из одной строки `@AGENTS.md`,
поэтому Codex (через `AGENTS.md`) и Claude Code (через `CLAUDE.md`) читают одни
и те же правила без дублирования. Все общие правила держите в корневом
`AGENTS.md`. Если подкаталогу нужны собственные правила, создайте рядом пару
`AGENTS.md` + `CLAUDE.md`, передав скрипту реальное правило:

```sh
./scripts/add-agent-scope.sh services/api "Run API tests before changing handlers."
```

```powershell
.\scripts\add-agent-scope.ps1 -Directory services/api -Rule "Run API tests before changing handlers."
```

Вложенные правила уточняют корневые и не должны им противоречить.

После создания проекта откройте его папку как отдельный Obsidian vault,
создайте отдельный GitHub-репозиторий и подключите `origin`.

## Главное правило

Не копируйте в Markdown данные, для которых уже есть первичный
машиночитаемый источник: OpenAPI, lock-файл, SBOM или `CODEOWNERS`. Markdown
должен объяснять и связывать эти источники.

Markdown-заметки связываются через wikilinks. Запись имени файла в обратных
кавычках показывает код, но не создаёт ребро в графе Obsidian. При изменении
этого универсального набора одновременно обновляются
[[GLOBAL_AGENT_INSTRUCTIONS]], bootstrap и шаблоны.
