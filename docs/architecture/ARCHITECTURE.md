---
type: architecture
status: active
owner: project
last_verified: 2026-08-03
source_of_truth: repository
related:
  - "[[PROJECT]]"
  - "[[INDEX]]"
  - "[[docs/architecture/decisions/ADR-0001-two-level-documentation|ADR-0001]]"
  - "[[docs/research/PROJECT_ARTIFACT_MODEL|PROJECT_ARTIFACT_MODEL]]"
  - "[[docs/architecture/ONE_C_CAPABILITY_PLAN|ONE_C_CAPABILITY_PLAN]]"
  - "[[docs/architecture/one-c/IMPLEMENTATION_PLAN|IMPLEMENTATION_PLAN]]"
---

# Архитектура

Проект состоит из семи слоёв:

1. `STANDARD_VERSION` и `config/` задают версию и машиночитаемый контракт
   профилей, policy blocks и index relationships.
2. [[GLOBAL_AGENT_INSTRUCTIONS]] задаёт поведение агента до открытия проекта.
3. [[AGENTS]] задаёт локальные правила конкретного репозитория.
4. [[TEMPLATES]] описывает переиспользуемые артефакты.
5. `scripts/` создаёт новый проект/repo внутри общего vault из выбранного
   профиля.
6. `.agents/skills/` хранит канонические Agent Skills для Codex, а
   `.claude/skills/` — минимальные мосты Claude Code к тем же workflow.
7. Capability — независимый от профиля слой поверх него. Он несёт основную
   сложность стандарта, и у него своя ось версий.

## Слой capability

Профиль отвечает на вопрос «какие документы у проекта есть». Capability отвечает
на другой: «какую работу проект умеет вести». Она подключается поверх любого
профиля не ниже своего минимума и не меняет его состав.

- `config/capabilities.tsv` — что и куда доставляется: источник, назначение,
  класс поставки (`template`, `verbatim`, `binary`) и политика владения
  (`managed` или `seed`). Класс отвечает на вопрос «можно ли подставлять
  значения», политика — на вопрос «кому принадлежит файл после установки».
- `config/capability-core.tsv` — минимальный профиль и обязательный стек.
  Capability с непустым `docs_section` требует профиля не ниже `software`: там
  появляется `docs/README.md`, без которого шаг индексации падает.
- `config/1c-routing.tsv` и `config/1c-artifacts.tsv` — для capability `1c`:
  первый решает, куда идёт каждый файл upstream, второй фиксирует результат
  пофайлово. `config/1c-release.json` хранит паспорт и `release_id` — хэш
  паспорта и ledger вместе.
- `.project-standard-artifacts.json` в созданном проекте — что фактически
  установлено. Сравнение его с release даёт план: создать, обновить, удалить
  или остановиться на конфликте.

У capability две половины, и путать их не стоит. **Поставка** отвечает на
вопрос «какие файлы у проекта появились и кому они принадлежат»: манифесты выше,
`capability_artifacts` как транзакция и `capability_install` как запись проекта
о себе — capability и установленный release в `.project-standard.json`, ссылки в
обоих индексах, стек практик. **Runtime** отвечает на другой вопрос — «что
проекту разрешено делать с живой системой», — и для `1c` это отдельный слой:
`one_c_session` (замок сессии: какая база, чем это подтверждено, разрешена ли
запись), `one_c_doctor` (диагностика только на чтение), `one_c_provider` и
`one_c_clients` (обнаружение внешнего MCP-провайдера и проекции клиентских
конфигураций с владением по имени), `one_c_setup`, `one_c_source`. По объёму это
большая часть кода стандарта; её решения и статусы живут в
[[docs/architecture/ONE_C_CAPABILITY_PLAN|мастер-плане]] и подпланах
[[docs/architecture/one-c/IMPLEMENTATION_PLAN|`one-c/`]], а проверенное
состояние — в [[docs/quality/READINESS_1C|матрице готовности]].

**Две оси версий, и их нельзя смешивать.** Схема стандарта — целое число, и
миграции идут по цепочке `from_schema → to_schema`. Версия capability — SemVer,
и обновление определяется сравнением `release_id`, а не шагом схемы. Поэтому
обработчик `capability_artifacts` объявлен внешним: он **никогда** не
появляется строкой в `config/migrations.tsv`, и планировщик миграций отвергает
такую строку с объяснением. Пустота манифеста здесь — выполненное требование, а
не незаконченная работа.

Инструкции агента имеют три разные области ответственности:

1. [[GLOBAL_AGENT_INSTRUCTIONS]] — переносимый источник глобальной политики
   компьютера; managed-копия живёт в `~/.codex/AGENTS.md`.
2. `templates/new-project/AGENTS.template.md` — источник project baseline и
   локальной идентичности для создаваемых и мигрируемых consumer projects.
3. [[AGENTS]] — локальные правила сопровождения самого репозитория стандарта;
   это не шаблон для других проектов.

Глобальная политика владеет полномочиями, Git safety, общим выбором инструментов,
иерархией инструкций и defaults новых проектов. Project baseline владеет
документацией, дефектами, playbook, Best Practices и локальным repository
workflow. Небольшой safety subset (язык, секреты, согласование зависимостей,
worktree isolation и инструкция `AGENTS.md`/`CLAUDE.md`) намеренно повторяется в
project baseline ради безопасной работы клонированного репозитория до завершения
глобальной настройки новой машины. Остальные межуровневые повторы запрещены.

Родительская рабочая папка является Obsidian vault. Каждый вложенный проект —
отдельный git-репозиторий без собственной `.obsidian`. Один набор Markdown-
файлов используется Obsidian и агентами (Codex, Claude Code) без копирования.
`.obsidian/` (включая device-specific `workspace.json`) принадлежит уровню
vault и никогда не коммитится в проектные репозитории; вложенные vault не
создаются, а шаблонный `.gitignore` защищает от случайного `.obsidian/`, если
проектную папку всё же откроют как отдельный vault. По этой же причине
community-решения уровня «vault = repo» (плагин obsidian-git, auto-commit,
mobile-sync внутри vault) к этой модели неприменимы.

Машиночитаемые источники истины не преобразуются в ручные Markdown-копии.

Скиллы используют общий стандарт `SKILL.md`. Инструкции не копируются между
агентами: Claude-мост указывает на канонический skill в `.agents/skills/`.
Документация хранит назначение, связи, ограничения и эксплуатационный контекст.

Оба bootstrap-адаптера читают `config/profiles.tsv` напрямую. Manifest задаёт
минимальный профиль, источник, destination и связи с обоими индексами;
platform-specific код отвечает только за запись generated artifacts, template
substitution, Git и безопасный rollback. Parity-тесты согласно
[[docs/architecture/decisions/ADR-0002-versioned-project-contract|ADR-0002]]
проверяют contract на обеих платформах и доказывают manifest-driven поведение в
изолированной копии.

**Ядро не знает, что такое capability изнутри.** `config/capability-core.tsv` —
единственный источник минимального профиля и обязательного стека: его читают оба
bootstrap и `project_metadata`, литералов в коде нет. Валидация, специфичная для
capability, живёт у самой capability (`scripts/one_c_validation.py`), а ядро
вызывает её через `CAPABILITY_VALIDATORS` — одна строка на capability — и
превращает возвращённые кортежи в findings. Вторая capability со своим реестром
пишет свой модуль и добавляет строку; `validate-project.py` при этом не
меняется. DSL валидации намеренно не вводится: у него пока один потребитель.

**Runtime сверяется с установленным release.** `one_c_release_guard` сравнивает
`capability_releases` проекта с паспортом чекаута. Там, где пишут — замок сессии
и рендерер клиентских проекций, — несовпадение это отказ; там, где только
читают, это строка отчёта, потому что диагностика не валит прогон. Отсутствие
capability в проекте несовпадением не считается, а нечитаемый паспорт чекаута
называется поломкой чекаута, а не виной проекта. Без этого строгость версий
заканчивалась ровно там, где начинается действие на живой системе.

`scripts/validate-project.py` является общей read-only validation logic на
Python 3.9 standard library. Native wrappers проверяют runtime и сохраняют
единые exit codes. Project doctor сначала выполняет platform environment check,
затем validator с дополнительной диагностикой Git, global agent policy и
родительского Obsidian vault. Auto-fix отсутствует: диагностика не владеет
пользовательскими файлами.

`scripts/standardize_existing_project.py` обслуживает только consumer projects.
До profile inference он определяет `target_kind`: полная совокупность rules
contract, validator, templates и skills означает `rules-repository`. Такой
target получает `not_applicable` report и не допускается к adopt/re-bootstrap
plan или apply; сам стандарт проверяется отдельными rules validation и audit
workflow. Это не позволяет self-assessment ошибочно превратить канонический
источник стандарта в consumer profile.

`scripts/sync_global_agents.py` отделяет portable policy от локальных
дополнений managed markers с текущей schema из `STANDARD_VERSION`. Read-only `check` и secret-safe `diff`
различают missing, legacy, conflict, match, drift и повреждённую grammar;
содержимое active file в отчёт не попадает. Текст вне managed block сохраняется
как пользовательский. Запись, backup и marker migration намеренно отложены до
отдельного подтверждаемого migration workflow.

`config/migrations.tsv` задаёт переходы schema и handlers. Общий
`scripts/project_metadata.py` реализует [[docs/architecture/PROJECT_STANDARD_SCHEMA|metadata schema]],
которую используют validator и `scripts/plan_migration.py`. Planner проверяет
точный профиль, clean Git trees и committed provenance, затем показывает
reviewable project JSON или secret-safe global structural plan. Текущая граница
apply требует точный fingerprint просмотренного плана и явный confirmation.
Перед записью planner повторяет preconditions: project target получает один
atomic-written unstaged metadata file, а global target — побайтовый timestamped
backup и atomic replace с сохранением внешнего пользовательского текста.

CI является отдельной trust boundary. Все external Actions pinned по full
commit SHA, workflow token read-only, а
`scripts/check-action-pins.py` проверяет policy до основных тестов. Dependabot
предлагает обновления SHA через PR. Ubuntu/Windows дают основной regression
gate; macOS smoke запускается вручную и при изменениях core paths. Угрозы и
residual risks описаны в [[docs/security/THREAT_MODEL]].

Связь с Best Practices удерживает
[[docs/architecture/BEST_PRACTICES_CONTRACT|pinned compatibility contract]].
Локальный CI без сети проверяет schema и ADR consequences, а maintainer перед
promotion сверяет соседний checkout по repository, commit, hashes, accepted
status и отсутствию retired routes. После структурных фаз GitHub governance
проверяется через API согласно [[docs/quality/PLAYBOOK|PLAYBOOK]].
