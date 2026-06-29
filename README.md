# Правила для нового проекта

Переносимый набор правил и шаблонов для создания проектов внутри общего
Obsidian vault. Каждый проект является отдельной папкой, корнем собственного
git-репозитория и локальной копией отдельного GitHub-репозитория.

Markdown редактируется напрямую в папке проекта. REST API, helper,
синхронизация и вторая копия заметок не требуются.

## Руководства

- [[docs/README|Документация проекта]]
- [[docs/guides/CREATE_NEW_PROJECT|Как создать новый проект]]
- [[docs/guides/SETUP_NEW_COMPUTER|Как подключить новый компьютер]]
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Как переносить знания между проектами]]

## Скиллы Codex и Claude Code

- [[.agents/skills/setup-new-computer/SKILL|setup-new-computer]] — проверяет и
  настраивает новый компьютер по общим правилам.
- [[.agents/skills/create-new-project/SKILL|create-new-project]] — создаёт,
  проверяет и публикует новый проект.
- [[.agents/skills/promote-project-knowledge/SKILL|promote-project-knowledge]] —
  превращает проверенный общий урок в правило, шаблон, тест или автоматизацию.

Канонические workflow находятся в `.agents/skills/` и автоматически
обнаруживаются Codex. Claude Code обнаруживает тонкие мосты в `.claude/skills/`,
которые загружают те же канонические файлы без дублирования инструкций.

## Использование на другом компьютере

1. Клонировать этот репозиторий.
2. Клонировать репозиторий внутрь общей папки Obsidian vault и открыть в
   Obsidian саму общую папку, а не вложенный проект.
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

Навигация по проекту в общем vault: [[INDEX|индекс]], [[PROJECT|описание проекта]],
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

- `minimal` — обязательное ядро (`README`, `AGENTS`, `CLAUDE`, `INDEX`,
  `PROJECT`) плюс `.editorconfig`, `.gitignore` и `.gitattributes`;
- `software` — ядро плюс индекс `docs/`, `CHANGELOG`, `ARCHITECTURE` и
  `TESTING`;
- `operated` — `software` плюс `ACTIONS`, `TOOLS`, `INTEGRATIONS` и
  `ENVIRONMENTS`;
- `all` — `operated` плюс `INTERFACES`, `DATA_MODEL`, `SECURITY` и
  `THREAT_MODEL`.

Канонический состав профилей и их связи с `INDEX.md`/`docs/README.md` хранит
`config/profiles.tsv`. Оба bootstrap-адаптера читают этот manifest напрямую;
parity-тесты проверяют фактический output на Windows и macOS/Linux.

Шаблоны «по одному файлу на экземпляр» — ADR, исследования, ревью, runbook и
postmortem — профиль намеренно не создаёт, чтобы не плодить пустые документы.
Они остаются в `templates/new-project/` и копируются вручную по мере
необходимости.

Bootstrap создаёт в каждом проекте `CLAUDE.md` из одной строки `@AGENTS.md`,
поэтому Codex (через `AGENTS.md`) и Claude Code (через `CLAUDE.md`) читают одни
и те же правила без дублирования. Созданный `AGENTS.md` требует давать все
ответы, исследования, ревью, планы и отчёты пользователю на русском языке,
если пользователь прямо не запросил другой язык. Все общие правила держите в
корневом `AGENTS.md`. Если подкаталогу нужны собственные правила, создайте рядом пару
`AGENTS.md` + `CLAUDE.md`, передав скрипту реальное правило:

```sh
./scripts/add-agent-scope.sh services/api "Run API tests before changing handlers."
```

```powershell
.\scripts\add-agent-scope.ps1 -Directory services/api -Rule "Run API tests before changing handlers."
```

Вложенные правила уточняют корневые и не должны им противоречить.

Создавайте проект внутри уже открытого общего Obsidian vault. Не превращайте
папку проекта в отдельный vault; создайте для неё отдельный GitHub-репозиторий
и подключите `origin`.

## Главное правило

Не копируйте в Markdown данные, для которых уже есть первичный
машиночитаемый источник: OpenAPI, lock-файл, SBOM или `CODEOWNERS`. Markdown
должен объяснять и связывать эти источники.

Markdown-заметки связываются через wikilinks. Запись имени файла в обратных
кавычках показывает код, но не создаёт ребро в графе Obsidian. При изменении
этого универсального набора одновременно обновляются
[[GLOBAL_AGENT_INSTRUCTIONS]], bootstrap и шаблоны.
