---
type: research
status: completed
owner: project
last_verified: 2026-06-27
source_of_truth: repository
related:
  - "[[PROJECT]]"
  - "[[INDEX]]"
  - "[[TOOLS]]"
  - "[[docs/research/PROJECT_ARTIFACT_MODEL|PROJECT_ARTIFACT_MODEL]]"
  - "[[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]]"
  - "[[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]]"
---

# Обязательная база инструментов проекта в 2026 году

## Краткий вывод

Для стека Codex + Claude Code + GitHub на macOS и Windows обязательная база
после Obsidian должна оставаться небольшой.

**На каждом рабочем компьютере обязательны:**

1. Git.
2. GitHub CLI (`gh`) с настроенной авторизацией.
3. Codex и Claude Code.
4. Системная командная среда: Zsh/Bash на macOS, PowerShell или Git Bash на
   Windows.
5. Безопасное хранилище учётных данных ОС; токены нельзя хранить в файлах
   проекта или в plaintext credential store.
6. Проверенный способ установки и обновления инструментов: Homebrew на macOS и
   WinGet на Windows являются предпочтительными, но не проектными зависимостями.

**В каждом репозитории обязательны:** Git-репозиторий с GitHub remote,
`README.md`, `AGENTS.md`, импортирующий его `CLAUDE.md`, `PROJECT.md`, `INDEX.md`,
`.gitignore` и `.gitattributes`. Для этого стандарта папка проекта одновременно
является git-root и Obsidian vault.

Python 3, PowerShell 7, standalone `ripgrep`, EditorConfig, CI, Dependabot,
Docker, Git LFS, pre-commit и языковые линтеры полезны, но не являются
универсальными обязательными зависимостями каждого проекта.

## Исследовательский вопрос

Какой минимальный набор инструментов в 2026 году действительно нужен каждому
новому проекту в нашем стеке, не создавая лишних зависимостей и сохраняя
переносимость между macOS и Windows?

## Метод

Исследование проведено 2026-06-27 по первичным официальным источникам OpenAI,
Anthropic, Git, GitHub, Microsoft, Python Software Foundation, EditorConfig,
Homebrew и Docker.

Кандидат считался обязательным только если он одновременно:

- нужен почти при любом типе проекта в нашем рабочем процессе;
- работает или имеет эквивалент на macOS и Windows;
- непосредственно поддерживает воспроизводимость, безопасность или работу
  обоих AI-агентов;
- не навязывает проекту конкретный язык, runtime или способ развёртывания;
- даёт пользу, превышающую стоимость установки и сопровождения.

Использованы четыре статуса:

| Статус | Значение |
|---|---|
| Обязательно на компьютере | Без этого основной рабочий процесс не считается настроенным |
| Обязательно в репозитории | Должно создаваться bootstrap-скриптом для каждого проекта |
| Рекомендуется | Устанавливается или включается по умолчанию при наличии пользы, но не блокирует старт |
| Условно | Добавляется только при появлении соответствующего кода, данных или эксплуатационного риска |

## Доказательства

### AI-агенты и инструкции

Codex рекомендует хранить устойчивые правила проекта в `AGENTS.md`, включая
реальные команды сборки, тестирования и проверки. В актуальном руководстве
Codex GitHub CLI указан как инструмент GitHub-функций, а для нативной работы в
Windows требуется Git. Источники: [Codex manual](https://developers.openai.com/codex/codex-manual.md),
[custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md).

Claude Code читает `CLAUDE.md`, поддерживает импорт `@AGENTS.md` и прямо
рекомендует такой импорт для совместимости с другими coding agents. На native
Windows Git for Windows рекомендуется, а при его отсутствии Claude Code
использует PowerShell. `ripgrep` обычно включён в поставку Claude Code, поэтому
отдельная установка `rg` не должна быть безусловным требованием. Источники:
[Claude Code memory](https://code.claude.com/docs/en/memory),
[Claude Code installation](https://code.claude.com/docs/en/installation).

### Git, GitHub и учётные данные

Git и GitHub CLI решают разные задачи: `git` управляет локальным и удалённым
репозиторием, а `gh` предоставляет terminal-доступ к pull requests, issues,
Actions, releases и GitHub API. Для нашего правила автоматического commit/push
и дальнейшей работы с GitHub оба инструмента входят в обязательную базу.
Источник: [About GitHub CLI](https://docs.github.com/en/github-cli/github-cli/about-github-cli).

Git поддерживает системные credential helpers. На macOS доступен Keychain, на
Windows — Credential Manager/Git Credential Manager. Встроенный
`git-credential-store` сохраняет секреты на диске без шифрования и не подходит
как стандарт. Источники: [Git credential helpers](https://git-scm.com/doc/credential-helpers),
[git-credential-store](https://git-scm.com/docs/git-credential-store).

`.gitignore` должен коммититься, чтобы правила исключения были общими для всех
клонов. `.gitattributes` особенно важен для macOS/Windows: Git рекомендует явно
нормализовать текст и задавать окончания строк для shell- и Windows-скриптов.
Источники: [Ignoring files](https://docs.github.com/en/get-started/git-basics/ignoring-files),
[gitattributes](https://git-scm.com/docs/gitattributes).

### Кроссплатформенная автоматизация

PowerShell 7 поддерживается на macOS и Windows, но в Windows устанавливается
рядом с Windows PowerShell 5.1, а не заменяет его. Следовательно, `pwsh` нужен
авторам и тестовым машинам, которые проверяют `.ps1`, но не каждому проекту.
Источники: [PowerShell on Windows](https://learn.microsoft.com/en-us/powershell/scripting/install/install-powershell-on-windows),
[PowerShell on macOS](https://learn.microsoft.com/en-us/powershell/scripting/install/install-powershell-on-macos).

Python удобен как общий runtime для нетривиальной автоматизации, и Codex
называет его распространённым рабочим инструментом. Однако Windows не содержит
системно поддерживаемую установку Python; её нужно добавлять отдельно. Поэтому
текущее правило «предпочитать standard library, только если Python доступен на
всех целевых машинах» корректнее, чем безусловная зависимость. Источники:
[Python on Windows](https://docs.python.org/3/using/windows.html),
[Python on macOS](https://docs.python.org/3/using/mac.html).

WinGet входит в современный Windows App Installer и управляет установкой и
обновлением приложений. Homebrew предоставляет аналогичный воспроизводимый
канал на macOS, но не является частью ОС. Это предпочтительные средства
подготовки компьютера, а не зависимости каждого репозитория. Источники:
[WinGet](https://learn.microsoft.com/en-us/windows/package-manager/winget/),
[Homebrew](https://brew.sh/).

### Качество и безопасность

GitHub Actions автоматизирует build, test и deployment и предоставляет runners
для Linux, Windows и macOS. Но workflow без реальной проверяемой команды создаёт
ложный сигнал качества. CI обязателен для проекта с исполняемыми проверками, но
не для пустого или только документального проекта. Источник:
[Understanding GitHub Actions](https://docs.github.com/actions/learn-github-actions/introduction-to-github-actions).

Dependency graph и Dependabot используют manifests и lockfiles. Их следует
включать, когда у проекта появляются поддерживаемые зависимости. Secret
scanning, push protection и code scanning полезны, но доступность части функций
зависит от visibility и GitHub plan. Источники:
[Supply chain security](https://docs.github.com/en/code-security/concepts/supply-chain-security/supply-chain-security),
[Securing a repository](https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository).

Rulesets позволяют требовать pull request, reviews и успешные status checks.
Это правильная защита для совместного или production-проекта, но она избыточна
для личного стартового репозитория, где принято немедленно отправлять изменения
в `origin/main`. Источник: [Rules available for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

EditorConfig переносит базовые правила форматирования между редакторами, но не
заменяет Git-нормализацию и языковой formatter. Docker даёт стандартизованное
окружение, однако добавляет отдельный runtime и лицензионные условия Docker
Desktop. Git LFS решает только задачу крупных бинарных файлов. Поэтому эти
инструменты нельзя включать в универсальное обязательное ядро. Источники:
[EditorConfig specification](https://spec.editorconfig.org/),
[Docker overview](https://docs.docker.com/get-started/docker-overview/),
[Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage).

### Ограничения исследования

Выводы относятся к заданному стеку и состоянию официальной документации на
2026-06-27. Исследование оценивает инженерную необходимость, а не популярность
инструментов. Доступность GitHub security-функций и системных package managers
нужно повторно проверять при изменении тарифа, ОС или корпоративных политик.

## Матрица решений

| Кандидат | Статус | Решение для стандарта |
|---|---|---|
| Git | Обязательно на компьютере | Проверять версию и доступность в `PATH`; на Windows искать также Git for Windows |
| GitHub CLI (`gh`) | Обязательно на компьютере | Проверять `gh auth status`; использовать для создания repo и GitHub-операций |
| Codex | Обязательно на компьютере | Глобальные правила в `~/.codex/AGENTS.md` |
| Claude Code | Обязательно на компьютере | `~/.claude/CLAUDE.md` импортирует общие правила |
| Безопасный credential helper | Обязательно на компьютере | Keychain/GCM; запрещать plaintext token files и `credential-store` |
| Shell ОС | Обязательно на компьютере | Zsh/Bash на macOS; PowerShell или Git Bash на Windows |
| Homebrew / WinGet | Рекомендуется | Стандартный канал установки и обновления; допускается официальный installer |
| Python 3 | Рекомендуется | Общая сложная автоматизация на stdlib; не использовать без проверки availability |
| PowerShell 7 | Рекомендуется maintainers | Нужен для разработки и runtime-проверки `.ps1`; не зависимость каждого проекта |
| `ripgrep` (`rg`) | Рекомендуется | Быстрый поиск; не устанавливать отдельно, если уже поставляется агентом |
| Редактор/IDE | Рекомендуется | Выбор пользователя; не фиксировать VS Code как обязательный |
| `.gitignore` | Обязательно в репозитории | Исключать секреты, local settings, caches и OS-файлы |
| `.gitattributes` | Обязательно в репозитории | Нормализовать текст; LF для `.sh`/Markdown, согласованная политика для `.ps1` |
| `.editorconfig` | Рекомендуется в репозитории | Низкая стоимость; согласует UTF-8, final newline и indentation между редакторами |
| Lockfile | Условно, затем обязательно | Коммитить, если выбранный package manager создаёт lockfile для приложения |
| GitHub Actions | Условно, затем обязательно | Добавлять после появления реальных lint/test/build checks |
| Dependabot | Условно | Включать при наличии поддерживаемых manifests/lockfiles |
| Secret scanning/push protection | Рекомендуется при доступности | Включать в GitHub settings с учётом visibility и plan |
| Branch rulesets | Условно | Для команды, production или защищаемого release-процесса |
| Docker/containers | Условно | Только когда проекту нужна изоляция сервисов или одинаковое runtime-окружение |
| Git LFS | Условно | Только для крупных бинарных файлов; обычный Git хранит исходники и Markdown |
| pre-commit framework | Условно | Только если локальные hooks дают доказуемую пользу и дублируются в CI |
| Языковые formatter/linter/test runner | Условно, затем обязательно | Выбираются после выбора языка; команды фиксируются в `AGENTS.md` |
| `jq`, Make, Task, just | Не входят в базу | Добавлять только при наличии повторяемого сценария, которого не покрывает текущий стек |

## Что не следует делать

- Не устанавливать Python только ради однострочной операции, доступной в shell
  или PowerShell.
- Не требовать Docker от документационного, мобильного или нативного проекта
  без контейнерного сценария.
- Не добавлять CI, который лишь завершается успешно и ничего не проверяет.
- Не вводить единый package manager для языков, пока язык проекта не выбран.
- Не дублировать секреты в `.env`, Markdown, scripts или agent instructions.
- Не считать наличие инструмента на одном Mac доказательством его доступности в
  Windows-клоне.

## Рекомендации к следующей версии bootstrap

1. Добавить read-only проверку компьютера с двумя реализациями (`.sh` и `.ps1`):
   обязательные `git`, `gh`, Codex, Claude Code, GitHub auth и credential helper;
   рекомендуемые Python, `pwsh`, `rg`, Homebrew/WinGet выводить отдельно.
2. Добавить `.editorconfig` во все bootstrap-профили; `.gitattributes` и
   `.gitignore` уже правильно входят в обязательное ядро.
3. В руководстве нового компьютера разделить «обязательно», «рекомендуется» и
   «только для разработки шаблона», чтобы PowerShell 7 и Python не выглядели
   скрытыми универсальными зависимостями.
4. В руководстве создания проекта добавить GitHub checklist: visibility,
   credential safety, security features при доступности и ruleset только при
   появлении совместной/production-разработки.
5. Для профиля `software` создавать CI только после обнаружения реальной
   проверочной команды; не генерировать фиктивный workflow.

## Заключение

Must-have в 2026 году для этого стека — не большой «универсальный toolchain», а
малое проверяемое ядро: Git, `gh`, два агента, безопасная авторизация, системная
командная среда и переносимые правила репозитория. Остальные инструменты должны
подключаться по сигналу проекта. Это уменьшает bootstrap, поверхность атак и
расхождение macOS/Windows, не мешая установить более сильный инструмент, когда
он действительно нужен.
