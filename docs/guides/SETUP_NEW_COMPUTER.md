---
type: guide
status: active
owner: project
last_verified: 2026-06-27
source_of_truth: repository
related:
  - "[[INDEX]]"
  - "[[README]]"
  - "[[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]]"
---

# Подключение нового компьютера

Эта настройка выполняется один раз на каждом новом компьютере. После неё Codex
и Claude Code используют общие глобальные правила, а проекты синхронизируются
через GitHub.

## 1. Подготовить программы

Нужны:

- Git;
- GitHub CLI `gh`;
- Obsidian;
- Codex;
- Claude Code, если он будет использоваться;
- PowerShell для запуска `.ps1` на Windows.

Проверьте доступность команд:

```sh
git --version
gh --version
```

```powershell
git --version
gh --version
$PSVersionTable.PSVersion
```

Если необходимой программы нет, попросите агента установить её. Агент должен
объяснить пакет и способ установки и получить разрешение до изменения системы.

## 2. Авторизовать GitHub

```sh
gh auth login
gh auth status
```

Используйте тот же GitHub-аккаунт, которому доступны приватные репозитории
`NightMadMax`.

## 3. Клонировать набор правил

```sh
gh repo clone NightMadMax/new-project-rules
cd new-project-rules
```

Локальную папку можно назвать `Правила для нового проекта`; имя GitHub-
репозитория при этом остаётся `new-project-rules`.

## 4. Открыть набор правил как Obsidian vault

В Obsidian выберите **Open folder as vault** и укажите клонированную папку.
Markdown редактируется напрямую в ней; отдельная копия и REST API не нужны.

## 5. Подключить глобальные инструкции агентов

Если `~/.codex/AGENTS.md` ещё отсутствует, setup создаст его из
[[GLOBAL_AGENT_INSTRUCTIONS]]. Если файл уже существует, сначала сравните и
объедините правила вручную: setup не перезаписывает пользовательские данные.

macOS/Linux:

```sh
./scripts/setup-global-agents.sh
```

Windows PowerShell:

```powershell
.\scripts\setup-global-agents.ps1
```

В результате:

```text
~/.codex/AGENTS.md       # глобальные правила, источник истины
~/.claude/CLAUDE.md      # одна строка: @~/.codex/AGENTS.md
```

Setup можно запускать повторно. Посторонние файлы и symlink он не
перезаписывает, а завершает работу с описанием конфликта.

## 6. Проверить загрузку инструкций

Для Codex запустите из любого проекта:

```sh
codex --ask-for-approval never "Summarize the current global and project instructions."
```

Для Claude Code откройте сессию и выполните:

```text
/memory
```

В списке должен присутствовать `~/.claude/CLAUDE.md`; импорт должен вести к
`~/.codex/AGENTS.md`.

## 7. Подключить существующий проект

Для уже существующего проекта bootstrap запускать нельзя. Нужно только
клонировать его и открыть клонированную папку как vault:

```sh
gh repo clone NightMadMax/project-repository
cd project-repository
git status
```

На Windows выполняются те же команды в PowerShell.

## 8. Работать с нескольких компьютеров

Перед началом работы:

```sh
git pull --ff-only
```

После завершения:

```sh
git add .
git commit -m "Describe the change"
git push
```

Codex по проектным правилам делает commit и push автоматически после
завершённых изменений, если пользователь не запретил синхронизацию.

Не редактируйте один и тот же незакоммиченный файл одновременно на двух
компьютерах. Сначала завершите и отправьте изменения на одном, затем выполните
`git pull --ff-only` на другом.

Obsidian workspace-файлы игнорируются git, поэтому расположение панелей остаётся
локальным. Markdown, шаблоны и общие правила синхронизируются через GitHub.

После настройки можно перейти к
[[docs/guides/CREATE_NEW_PROJECT|созданию нового проекта]].
