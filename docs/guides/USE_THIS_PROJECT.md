---
type: guide
status: active
owner: project
last_verified: 2026-07-02
source_of_truth: repository
related:
  - "[[README]]"
  - "[[INDEX]]"
  - "[[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]]"
  - "[[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]]"
  - "[[docs/guides/ASSESS_EXISTING_PROJECT|ASSESS_EXISTING_PROJECT]]"
  - "[[docs/guides/STANDARDIZE_EXISTING_PROJECT|STANDARDIZE_EXISTING_PROJECT]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/guides/SYNC_GLOBAL_AGENTS|SYNC_GLOBAL_AGENTS]]"
  - "[[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY|AI_KNOWLEDGE_PORTABILITY]]"
---

# Как работать с этим проектом

Этот проект нужен не для разработки одного приложения, а как рабочий набор
правил, шаблонов, скриптов и agent workflow для типовых задач:

- создать новый проект по стандарту;
- подключить новый компьютер;
- оценить существующий проект без изменений;
- стандартизировать legacy-проект безопасным способом;
- проверить среду, структуру проекта и состояние глобальных правил;
- перенести повторяемые знания из одного проекта в общий стандарт;
- записать урок после ошибки или удачного повторённого подхода.

## Самая короткая модель использования

Есть два режима работы:

1. Попросить агента сделать задачу.
2. Запустить нужный `scripts/*` инструмент вручную.

По умолчанию удобнее просить агента, а ручные команды использовать, когда нужен
точный контроль, повторяемость или локальная проверка без агентского workflow.
Точные команды для ручного запуска — в
[[docs/guides/MANUAL_SCRIPTS|MANUAL_SCRIPTS]].

## Как формулировать запросы агенту

Хороший запрос почти всегда содержит:

- что именно нужно сделать;
- путь к целевому проекту или папке;
- профиль (`minimal`, `software`, `operated`, `all`), если речь о bootstrap;
- ограничения безопасности: `read-only`, `ничего не удаляй`,
  `не устанавливай без разрешения`, `сначала покажи план`;
- ожидание по GitHub: нужен отдельный репозиторий или нет.

Базовый шаблон:

> Сделай `<действие>` для `<путь или проект>`. Используй `new-project-rules`.
> Сначала покажи план. Ничего не устанавливай без моего разрешения.

## Какими фразами просить типовые действия

### 1. Создать новый проект

Codex: `$create-new-project`

Claude Code: `/create-new-project`

Фразы:

> Создай новый проект «Название» в папке `<путь>`, профиль `software`,
> приватный GitHub-репозиторий.

> Создай новый local-only проект «Название» в папке `<путь>`, профиль
> `minimal`, без GitHub-репозитория.

> Создай новый проект «Название» внутри общего Obsidian vault, профиль
> `operated`, сначала покажи план файлов и репозитория.

Когда использовать:

- старт нового проекта с нуля;
- нужен готовый каркас файлов, `AGENTS.md`, `CLAUDE.md`, `INDEX.md`,
  `PROJECT.md` и подходящий набор `docs/`.

На финальном шаге агент предлагает (opt-in) подтянуть практики из соседней базы
Best Practices: общие (`common`) — сразу, стековые — когда определится стек. При
необходимости он обновит базу или установит её, если её нет; ваш отказ
фиксируется в `.best-practices.json`, чтобы не спрашивать повторно.

Подробности: [[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]].

### 2. Подключить новый компьютер

Codex: `$setup-new-computer`

Claude Code: `/setup-new-computer`

Фразы:

> Настрой новый компьютер для работы с общим Obsidian vault и проектами
> `NightMadMax`. Используй `new-project-rules`, режим `codex`, ничего не
> устанавливай без моего разрешения.

> Проверь новый компьютер для `both`: Codex и Claude Code. Покажи, чего не
> хватает, и сначала предложи план настройки.

Когда использовать:

- новый Mac или Windows-компьютер;
- нужно настроить `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`, GitHub, doctor,
  global policy sync.

Подробности: [[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]].

### 3. Оценить существующий проект без изменений

Codex: `$assess-existing-project`

Claude Code: `/assess-existing-project`

Фразы:

> Оцени существующий проект `<path>` относительно `new-project-rules` и скажи,
> можно ли безопасно привести его к стандарту на месте.

> Подготовь read-only decision report для проекта `<path>`: какой профиль ближе,
> какие блокеры есть и стоит ли делать `adopt-in-place`.

Когда использовать:

- проект уже существует;
- сначала нужен анализ, а не правки.

Подробности: [[docs/guides/ASSESS_EXISTING_PROJECT|ASSESS_EXISTING_PROJECT]].

### 4. Стандартизировать существующий проект

Codex: `$standardize-existing-project`

Claude Code: `/standardize-existing-project`

Фразы:

> Приведи существующий проект `<path>` к стандарту `new-project-rules`, ничего
> не удаляй без согласования.

> Посмотри проект `<path>` и предложи две стратегии: `adopt-in-place` или
> `re-bootstrap-from-existing`.

> Создай новый проект по правилам на основе существующего `<path>` и перенеси
> только код, тесты и безопасные конфиги.

Когда использовать:

- проект уже живёт своей жизнью;
- нужен controlled migration к стандарту.

Подробности:
[[docs/guides/STANDARDIZE_EXISTING_PROJECT|STANDARDIZE_EXISTING_PROJECT]].

### 5. Проверить проект или набор правил

Фразы:

> Проверь этот репозиторий validator-ом и коротко скажи, что не так.

> Запусти doctor для этого проекта и покажи только реальные проблемы.

> Проверь текущий проект как `software` profile без изменения файлов.

Когда использовать:

- нужна структурная проверка проекта;
- нужно понять, чего не хватает для стандарта;
- нужно быстро диагностировать окружение или репозиторий.

Подробности:
[[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE]].

### 6. Проверить глобальные правила агентов

Фразы:

> Проверь, синхронизированы ли глобальные правила Codex и Claude Code.

> Покажи read-only diff между portable global instructions и моим
> `~/.codex/AGENTS.md`.

> Построй план миграции для глобальных agent rules, но ничего не применяй.

Когда использовать:

- менялись глобальные правила;
- нужно проверить drift;
- нужно подготовить безопасную миграцию с fingerprint.

Подробности:
[[docs/guides/SYNC_GLOBAL_AGENTS|SYNC_GLOBAL_AGENTS]] и
[[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]].

### 7. Построить или применить migration plan

Фразы:

> Построй read-only migration plan для project metadata в `<path>`.

> Построй global migration plan и объясни preconditions простыми словами.

> Применяй migration только после того, как покажешь fingerprint и список
> изменений.

Когда использовать:

- нужно перейти на новую схему `.project-standard.json`;
- нужно применить managed global policy безопасным способом;
- важны preview и rollback.

Подробности: [[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]].

### 8. Перенести знания в общий стандарт

Codex:

- `$promote-project-knowledge`
- `$harvest-project-lessons`
- `$apply-promotion-candidate`

Claude Code:

- `/promote-project-knowledge`
- `/harvest-project-lessons`
- `/apply-promotion-candidate`

Фразы:

> Посмотри, есть ли в проекте повторяемый lesson, который нужно поднять в
> `new-project-rules`.

> Собери кандидатов на promotion из проекта `<path>` и подготовь shortlist.

> Примени approved promotion candidate в шаблоны, guides или skills.

Когда использовать:

- найден повторяемый дефект, правило или удачный workflow;
- знание должно жить не только в одном проекте.

Подробности:
[[docs/guides/AI_KNOWLEDGE_PORTABILITY|AI_KNOWLEDGE_PORTABILITY]].

### 9. Записать урок после ошибки или поправки

Codex: `$reflect-and-record`

Claude Code: `/reflect-and-record`

Фразы:

> Ты только что ошибся: `<что произошло>`. Отрефлексируй корневую причину и
> запиши урок туда, где ему место.

> Зафиксируй этот вывод так, чтобы он не потерялся: дефект, паттерн или
> правило — реши сам и объясни выбор.

Когда использовать:

- агент ошибся или пользователь его поправил;
- найден дефект, который нужно записать в
  [[docs/quality/DEFECTS|DEFECTS]];
- подход сработал повторно и заслуживает записи в
  [[docs/quality/PLAYBOOK|PLAYBOOK]].

Подробности: [[.agents/skills/reflect-and-record/SKILL|reflect-and-record]].

### 10. Сжать накопившийся «мусор» проекта

Codex: `$compress-project`

Claude Code: `/compress-project`

Фразы:

> Проект оброс — сделай отчёт о компрессии и покажи, что можно безопасно
> убрать.

> Проведи компрессию проекта: журналы и docs. Память агентов тоже разбери,
> но только с показом дублей и без удаления.

Когда использовать:

- журналы, research/audit или навигация разрослись за долгую работу;
- периодическая уборка или подготовка к релизу.

Только скрипт-отчёт без скилла: `./scripts/compress-project.sh --root .`.
Подробности: [[docs/guides/COMPRESS_PROJECT|COMPRESS_PROJECT]].

## Полезные уточнения в запросе

Чтобы агент работал предсказуемо, добавляйте короткие ограничения:

- `Сначала покажи план.` — если хотите review перед изменениями.
- `Ничего не применяй без подтверждения fingerprint.` — для migration workflow.
- `Только read-only.` — для assessment, doctor, sync, diff, review.
- `Ничего не удаляй без согласования.` — для legacy-проектов.
- `Не устанавливай инструменты без моего разрешения.` — для нового компьютера.
- `Сделай commit и push после проверки.` — если нужна синхронизация.
- `Не делай push.` — если изменения должны остаться локальными.

## Как понять, какой workflow выбрать

| Ситуация | Что просить |
|---|---|
| Нужен новый проект с нуля | `create-new-project` |
| Новый компьютер ещё не настроен | `setup-new-computer` |
| Есть legacy-проект и сначала нужен анализ | `assess-existing-project` |
| Есть legacy-проект и уже нужна controlled стандартизация | `standardize-existing-project` |
| Нужно проверить структуру и среду | validator / doctor |
| Нужно проверить или подтянуть global instructions | sync-global-agents / plan-migration |
| Нужно вынести lesson в общий стандарт | knowledge portability workflows |
| Агент ошибся или найден урок, который нельзя терять | `reflect-and-record` |
| Проект оброс мусором за долгую работу | `compress-project` |

## Если не хотите помнить названия skill

Можно писать без `$skill-name` и без `/skill-name`, обычным языком. Главное —
чётко описать задачу и ограничения.

Рабочие примеры:

> Создай новый проект по этому стандарту.

> Оцени существующий проект без изменений и скажи, можно ли стандартизировать
> его на месте.

> Проверь, не разъехались ли глобальные правила Codex и Claude Code.

> Настрой этот компьютер для работы с моими проектами и ничего не устанавливай
> без разрешения.

Агент должен сам сопоставить такую формулировку с нужным workflow.

## Что просить не стоит

Плохие формулировки слишком короткие и не задают границы:

- `Сделай проект.` — непонятны путь, профиль и GitHub.
- `Почини всё.` — непонятно, это read-only проверка или реальные правки.
- `Обнови правила.` — непонятно, проектные или глобальные, с apply или без.

Лучше так:

> Проверь текущий репозиторий validator-ом как `software` profile и покажи
> только реальные несоответствия.

> Обнови глобальные правила только через migration plan, без apply.

## Следующие документы

- [[docs/guides/CREATE_NEW_PROJECT|Создание нового проекта]]
- [[docs/guides/SETUP_NEW_COMPUTER|Подключение нового компьютера]]
- [[docs/guides/ASSESS_EXISTING_PROJECT|Оценка существующего проекта]]
- [[docs/guides/STANDARDIZE_EXISTING_PROJECT|Стандартизация существующего проекта]]
- [[docs/guides/VALIDATE_AND_DIAGNOSE|Валидация и диагностика]]
- [[docs/guides/SYNC_GLOBAL_AGENTS|Синхронизация глобальных правил]]
- [[docs/guides/PLAN_MIGRATIONS|Планирование миграций]]
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Перенос знаний]]
