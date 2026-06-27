# Правила для нового проекта

Переносимый набор правил и шаблонов для создания проектов, в которых одна и та
же папка одновременно является:

- Obsidian vault;
- корнем git-репозитория;
- локальной копией отдельного GitHub-репозитория.

Markdown редактируется напрямую в папке проекта. REST API, helper,
синхронизация и вторая копия заметок не требуются.

## Использование на другом компьютере

1. Клонировать этот репозиторий.
2. Открыть клонированную папку в Obsidian через **Open folder as vault**.
3. Перенести содержимое `GLOBAL_AGENT_INSTRUCTIONS.md` в глобальный
   `~/.codex/AGENTS.md`, сохранив уже существующие инструкции этого компьютера.
4. Для нового проекта запустить один из bootstrap-скриптов.

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

После создания проекта откройте его папку как отдельный Obsidian vault,
создайте отдельный GitHub-репозиторий и подключите `origin`.

## Главное правило

Не копируйте в Markdown данные, для которых уже есть первичный
машиночитаемый источник: OpenAPI, lock-файл, SBOM или `CODEOWNERS`. Markdown
должен объяснять и связывать эти источники.
