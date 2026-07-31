---
type: implementation-subplan
status: accepted
owner: project
last_verified: 2026-07-25
source_of_truth: repository
related:
  - "[[docs/architecture/ONE_C_CAPABILITY_PLAN]]"
  - "[[docs/guides/CREATE_NEW_PROJECT]]"
  - "[[docs/architecture/ARCHITECTURE]]"
---

# Capability `1c`: среда и установка компонентов

Этот подплан конкретизирует раздел среды мастер-плана
[[docs/architecture/ONE_C_CAPABILITY_PLAN|capability `1c`]]. Решения здесь
утверждены; реализация начнётся только после итогового утверждения мастер-плана.

## Базовая среда

Windows — исходная система, а не устанавливаемый компонент. Runtime-операции
1С выполняются на Windows; создание репозитория, Git, документация и
статические проверки остаются кросс-платформенными.

На не-Windows `doctor-1c` не предлагает установить ОС. Он блокирует только
Windows runtime и продолжает доступные проверки. После клонирования проекта на
Windows setup запускается повторно.

## Интерактивный контракт

Последовательность для пользователя:

```text
create-new-project → setup-1c-environment → doctor-1c
```

`create-new-project` создаёт и валидирует только репозиторий.
`doctor-1c` read-only определяет фактическое состояние.
`setup-1c-environment` меняет машину только после явного разрешения.

Для каждого компонента до вопроса показываются:

- зачем он устанавливается;
- какие функции включает;
- класс `required`, `conditional` или `optional`;
- что перестанет работать при отказе;
- рекомендуемая или обнаруженная версия;
- официальные страницы загрузки и документации;
- требования admin, restart, network, credentials и license.

Отсутствующий компонент: `установить автоматически`, `установить
самостоятельно` или `пропустить`. Найденный: `использовать`,
`обновить/переустановить` или `не использовать`. Перед автоматической
установкой показываются команда, источник, версия и область изменений. После
любого варианта результат проверяется фактически.

Пропуск `required` даёт итог `incomplete`; пропуск `conditional` перечисляет
отключённые функции; пропуск `optional` не влияет на основной статус.

## Каталог компонентов

Таблица собирается из `config/1c-components.tsv` — источника, из которого
исполнитель строит prompt. Пересобрать: `python3 scripts/one_c_components.py --table`.

<!-- generated from config/1c-components.tsv -->

| Компонент | Класс | Зачем | Установка | Требуется заранее | Результат пропуска |
|---|---|---|---|---|---|
| Git for Windows | required | Версионирование, синхронизация и откат проекта | manual; <https://git-scm.com/download/win> | нет | Полноценная работа с проектом невозможна |
| Python 3.9+ | required | Валидаторы, миграции и скрипты стандарта | manual; <https://www.python.org/downloads/windows/> | нет | Статус incomplete: проверки стандарта не запускаются |
| Платформа 1С | required | Runtime баз и встроенный сервер Toolkit | assisted; <https://releases.1c.ru/project/Platform83> | нет | Базы и Toolkit не запускаются |
| 1C:EDT | required | Разработка, метаданные, ошибки и отладка | manual; <https://edt.1c.ru/> | платформа 1С нужной ветки | Нет полноценной 1С-разработки |
| EDT-MCP | required | Доступ AI-клиента к workspace EDT | assisted; <https://github.com/DitriXNew/EDT-MCP> | установленная совместимая 1C:EDT | AI-клиент не управляет EDT |
| Docker Desktop | required | Внешние контейнерные MCP | manual; <https://docs.docker.com/desktop/setup/install/windows-install/> | WSL 2, Virtual Machine Platform, виртуализация в BIOS/UEFI, служба LanmanServer | Недоступны container MCP |
| Внешний MCP provider | required | Готовая поставка контейнерных MCP-серверов | reuse; <https://vibecoding1c.ru/mcp_server> | Docker Desktop | MCP-зависимая разработка неполна |
| Доступ к 1С:Напарнику | required | Токен для CodeChecker, ревью и правки BSL | manual; <https://code.1c.ai/tokens/> | нет | CodeChecker недоступен |
| Плагин обычного приложения | conditional | Запуск баз с application_kind=ordinary из EDT | manual; <https://github.com/bia-technologies/edt-runordinaryapplication-plugin/releases/latest> | установленная 1C:EDT | Обычные приложения не запускаются из EDT |
| Патч Run without update | conditional | Запуск без обновления конфигурации базы | manual; `config/1c-release.json` | установленная 1C:EDT | Эта функция недоступна |
| Node.js | conditional | Runtime для md-to-docx и OpenSpec CLI | manual; <https://nodejs.org/en/download> | нет | Отключаются выбранные Node-функции |
| npm package docx | conditional | Генерация DOCX из Markdown | project-local: `npm ci --prefix .agents/skills/md-to-docx`; <https://www.npmjs.com/package/docx> | Node.js | Недоступен md-to-docx |
| Pillow | conditional | Обработка изображений для разметки сетки | project-local: `{python} -m pip install pillow`; <https://pillow.readthedocs.io/en/stable/installation/index.html> | нет | Недоступен анализ сетки на изображении |
| YAxUnit | conditional | Модульные тесты BSL | manual; <https://bia-technologies.github.io/yaxunit/> | платформа 1С и непроизводственная база | Модульные тесты недоступны, остаются syntax и smoke |
| BSL Language Server standalone | conditional | Проверка репозитория вне MCP-сессии | manual; <https://github.com/1c-syntax/bsl-language-server/releases> | нет | Проверка BSL доступна только через Syntax MCP в сессии агента |
| v8unpack | conditional | Offline unpack и repack CF, CFE и EPF | project-local: `{python} -m pip install v8unpack`; <https://pypi.org/project/v8unpack/> | нет | Недоступен v8unpack-cf |
| OpenSpec CLI | conditional | CLI-операции OpenSpec | manual; <https://github.com/Fission-AI/OpenSpec/blob/main/docs/installation.md> | Node.js не ниже 20.19.0 | Markdown и AI workflow остаются, CLI отключён |
| uv | optional | Управление Python environments | manual; <https://docs.astral.sh/uv/getting-started/installation/> | нет | Используются venv и pip |

<!-- /generated -->

## Версии

- Рекомендуется последний стабильный **1C:EDT 2026.x**, не release candidate.
  Конкретный patch обновляется build-time release.
- EDT-MCP обязан быть совместим с выбранной EDT; build-time release хранит
  проверенную пару.
- Для существующей базы используется её ветка платформы. Совместимость
  проверяется по матрице EDT, а не простым сравнением с одним общим минимумом.
  Текущая официальная матрица включает:

  | Ветка платформы | Минимальная сборка |
  |---|---:|
  | 8.3.24 | 8.3.24.1819 |
  | 8.3.25 | 8.3.25.1633 |
  | 8.3.26 | 8.3.26.1656 |
  | 8.3.27 | 8.3.27.2025 |
  | 8.5.1 | 8.5.1.1423 |

- При свежей установке Node.js рекомендуется текущая LTS. Для OpenSpec CLI
  требуется Node.js `>=20.19.0`; `md-to-docx` проверяет собственный диапазон.
- Конкретные versions, sources и hashes хранятся в
  `config/1c-release.json`; `TOOLCHAIN.md` созданного проекта фиксирует
  обнаруженное состояние.

## Windows prerequisites

Они не являются самостоятельными компонентами проекта. Setup раскрывает их
только внутри шага Docker:

| Prerequisite | Поведение |
|---|---|
| WSL 2 | Проверить; при отсутствии предложить `wsl --install --no-distribution` |
| Windows Subsystem for Linux | Включается штатной установкой WSL после approval |
| Virtual Machine Platform | Включается штатной установкой WSL после approval |
| BIOS/UEFI virtualization | Только обнаружить и дать ручную инструкцию |
| `LanmanServer` | Проверить; при необходимости предложить включить |

Включение WSL требует admin и может потребовать restart. После перезагрузки
setup продолжает с повторной проверки. Linux-дистрибутив пользователю не
устанавливается: Docker Desktop создаёт собственную WSL-среду.

Не включаются без отдельной реальной зависимости:

- Hyper-V;
- Windows Containers;
- Ubuntu или другой пользовательский WSL-дистрибутив;
- отдельный Docker Compose.

## Не отдельные установки

- Windows и Windows PowerShell 5.1 — базовая среда, только проверяются.
- Java поставляется с EDT 2025.1+; отдельный JDK пользователю не нужен.
- Штатный CLI EDT входит в поставку EDT и используется для конвертации
  EDT-формата в XML (решение 1.21); отдельная установка не требуется,
  `doctor-1c` проверяет доступность и версию.
- Плагин 1С:Напарник входит в EDT 2025+; отдельно настраивается только токен.
- `npm` входит в Node.js, Docker Compose — в Docker Desktop.
- BSL Language Server находится внутри Syntax MCP container.
- Maven и build JDK нужны только maintainer build-time. Патчи EDT-MCP и
  обычного приложения приходят пользователю готовыми и проверенными по hash.
- Codex и Claude Code не устанавливаются setup. Текущий клиент
  переиспользуется; поздний подключается через
  `activate-1c-client codex|claude`.
- Toolkit EPF входят в release; setup проверяет SHA-256 и создаёт профили.
- Transcribe, Whisper, ffmpeg и Gemini исключены из capability `1c`.

## EDT и связанные компоненты

Порядок:

1. Платформа 1С нужной ветки.
2. Стабильная EDT 2026.x с bundled Java и плагином Напарника.
3. Совместимый EDT-MCP.
4. Токен Напарника в локальном runtime state.
5. Плагин обычного приложения — только для `ordinary`.
6. `Run without update` — только при выборе этой функции.
7. Project-managed launch profiles.

Базовый EDT-MCP устанавливается без локальной адаптации. Патчи собираются на
build-time из pinned sources и применяются только к совместимым версиям. Если
проверенной сборки нет, conditional-функция честно помечается недоступной.

## Внешний MCP provider

Provider — одна внешняя поставка, а не набор независимых установок.
Capability не создаёт второй комплект контейнеров и не владеет их lifecycle.
При наличии локального дистрибутива setup может по approval вызвать штатный
installer provider; без дистрибутива показывает официальный источник и ждёт
ручного получения.

Начальный обязательный набор:

- SyntaxCheckServer;
- HelpSearchServer;
- SSLSearchServer;
- TemplatesSearchServer;
- 1CCodeChecker.

Дополнительные роли включаются отдельно:

- CodeMetadataSearchServer — после подготовки source inputs;
- GraphMetadataSearch — после подготовки index/Neo4j;
- Data MCP — по умолчанию выключен до отдельного security review.

Остановленный Docker `1c-mcp-toolkit-proxy` не используется: Toolkit работает
через встроенный HTTP-сервер EPF.

## Проверка

Если официальный источник требует входа, пользователь проходит его сам.

После каждого домена и в конце запускается `doctor-1c`. Он проверяет факты, но
ничего не устанавливает:

- версии и совместимость;
- наличие bundled-компонентов;
- Docker/WSL и provider health/identity/tools;
- токен через безопасный health-check без вывода значения;
- plugin/patch state;
- профили и SHA-256 Toolkit;
- доступность CLI EDT для конвертации формата исходников.

Ошибка setup не откатывает готовый репозиторий и не маскируется как успех:
отчёт отдельно показывает готовые, отсутствующие, пропущенные и ожидающие
ручного шага компоненты.
