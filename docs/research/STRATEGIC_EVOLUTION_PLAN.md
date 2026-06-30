---
type: research
status: accepted
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[PROJECT]]"
  - "[[docs/architecture/ARCHITECTURE]]"
  - "[[docs/research/PROJECT_ARTIFACT_MODEL]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY]]"
  - "[[docs/quality/TESTING]]"
  - "[[docs/quality/DEFECTS]]"
---

# Стратегический план развития

## Цель

Превратить `new-project-rules` из надёжного набора bootstrap-скриптов в
версионируемую policy-систему для создания, проверки и безопасного обновления
проектов и глобальных правил агента.

Целевая система должна отвечать на четыре вопроса:

1. Какой стандарт и профиль применены к конкретному проекту?
2. Соответствует ли проект текущему контракту без перезаписи его собственных
   решений?
3. Какие изменения нужны для перехода между версиями стандарта?
4. Совпадают ли глобальные инструкции компьютера с переносимой политикой?

## Текущая база

Уже работают:

- четыре bootstrap-профиля и отдельный git-root на проект;
- native shell и PowerShell entry points;
- global, project и scoped agent instructions;
- Agent Skills для настройки компьютера, создания проекта и promotion знаний;
- regression tests на Ubuntu и Windows;
- rollback bootstrap, профильные docs indexes и agent-mode environment checks;
- defect log, ADR, research, reviews и Obsidian navigation.

Стратегический этап не должен ломать этот zero-surprise workflow или требовать
миграции всех существующих проектов одним действием.

## Статус реализации

| Этап | Статус | Результат |
|---|---|---|
| A. ADR и contract skeleton | completed | `STANDARD_VERSION=1`, TSV fixtures и parity tests |
| B. Manifest-driven bootstrap | completed | оба adapters читают `config/profiles.tsv` напрямую |
| C. Validator и doctor | completed | read-only validator, wrappers, doctor и report-only CI |
| D. Global sync | completed | managed-block grammar, read-only check/diff и confirmed migration apply |
| E. Migration engine | completed | manifest, schema, fingerprint, clean guards, backup и atomic project/global apply |
| F. Supply-chain hardening | repository completed / platform blocked | SHA pins, Dependabot, pin policy, threat model и macOS smoke; ruleset недоступен на текущем GitHub plan |

## Целевая архитектура

```text
Canonical Project Contract
├── standard version
├── profile and artifact manifest
├── required policy blocks
├── index relationships
└── validation rules
        │
        ├── bootstrap adapters: sh / PowerShell
        ├── project validator
        ├── global rules sync: check / diff / apply
        ├── migration planner and executor
        ├── Agent Skills
        └── conformance suite and CI
```

Предлагаемый пользовательский интерфейс:

```text
project-rules bootstrap
project-rules validate
project-rules doctor
project-rules sync-agents --check|--diff|--apply
project-rules migrate --plan|--apply
```

Это логические команды. Они могут оставаться отдельными `.sh`/`.ps1`
entry points; единый бинарник не является обязательной целью.

## Поток 1. Канонический контракт

### Задача

Убрать скрытую договорённость между двумя bootstrap-реализациями и сделать
состав профилей машиночитаемым.

### Артефакты

- `STANDARD_VERSION` — версия схемы стандарта, не marketing release;
- `config/profiles.tsv` — профиль, template, destination, индекс и назначение;
- `config/policy-contract.txt` — обязательные section headings и invariants;
- schema documentation с правилами совместимости.

TSV предлагается потому, что его можно безопасно читать POSIX shell и
PowerShell без `jq`, YAML parser или новой runtime-зависимости.

### Проверки готовности

- обе bootstrap-реализации получают состав файлов из одного manifest;
- один artifact нельзя добавить только в одну платформенную реализацию;
- неизвестная версия или некорректная строка manifest завершают работу до
  изменения destination;
- profiles сохраняют текущий состав файлов и проходят snapshot tests.

## Поток 2. Versioned project state

### Задача

Дать каждому созданному проекту проверяемую идентичность стандарта.

### Предлагаемый файл

`.project-standard.json`:

```json
{
  "schema_version": 1,
  "profile": "software",
  "source": "NightMadMax/new-project-rules",
  "source_commit": "<commit>",
  "created_at": "YYYY-MM-DD"
}
```

Файл содержит только происхождение bootstrap и не хранит секреты, локальные
пути или изменяемое описание проекта.

### Проверки готовности

- metadata создаётся детерминированно и коммитится вместе с проектом;
- старый проект без metadata определяется как `legacy`, а не как повреждённый;
- validator различает schema version и release version;
- пользователь может явно выбрать local-only source без выдуманного GitHub URL.

## Поток 3. Project validator

### Режимы

- `validate new-project-rules` — проверка самого набора правил;
- `validate generated-project` — проверка созданного проекта;
- `doctor` — диагностика окружения и объяснение исправлений без mutation.

### Минимальные проверки

- required core и профильные artifacts;
- `CLAUDE.md` как точный импорт `@AGENTS.md`;
- полнота `INDEX.md` и `docs/README.md`;
- разрешимость wikilinks;
- обязательные frontmatter fields и ISO dates;
- отсутствие `.obsidian`, template placeholders и raw memory directories;
- отсутствие известных secret patterns и абсолютных machine-specific paths;
- согласованность standard version, profile и фактического дерева;
- чистота или явно разрешённое состояние Git перед mutation.

### Runtime

Рекомендуется гибридная модель:

- bootstrap и базовый doctor остаются native shell/PowerShell без Python;
- сложный validator и migrator используют Python 3 standard library;
- wrappers проверяют Python до запуска и объясняют установку, но не ставят его
  без разрешения;
- CI фиксирует минимальную поддерживаемую версию Python.

Это решение требует отдельного утверждения, потому что добавляет runtime для
расширенных операций, хотя не блокирует базовый bootstrap.

## Поток 4. Безопасная синхронизация global rules

### Команды

- `--check` — только exit code и краткий статус;
- `--diff` — secret-safe diff без изменения файлов;
- `--apply` — backup, preview и применение после явного подтверждения;
- `--force` не добавлять в первую версию.

### Модель владения

Рекомендуется управляемый блок внутри `~/.codex/AGENTS.md`:

```text
<!-- new-project-rules:begin schema=1 -->
...portable managed policy...
<!-- new-project-rules:end -->
```

Текст вне блока остаётся пользовательским и никогда автоматически не
перезаписывается. Первый переход существующего файла в managed-block model
должен быть отдельной подтверждаемой миграцией.

### Проверки готовности

- `--check` ничего не пишет;
- `--apply` создаёт timestamped backup;
- конфликт или повреждённые markers останавливают операцию;
- повторный apply идемпотентен;
- Claude import остаётся одной строкой и проверяется отдельно;
- raw Codex/Claude memory не входит в синхронизацию.

## Поток 5. Миграции проектов

### Основные правила

- `--plan` является default и ничего не меняет;
- `--apply` требует чистого git working tree;
- миграция не переписывает пользовательский текст без managed markers;
- каждый migration имеет уникальный ID, from/to schema version и tests;
- применённые migration IDs записываются в `.project-standard.json`;
- повторный запуск безопасен;
- откат выполняется через отдельный git commit, а не скрытый backup tree.

### Структура

```text
migrations/
├── 0001-add-project-standard/
│   ├── PLAN.md
│   └── migrate.py
└── 0002-example/
```

`PLAN.md` объясняет intent и границы, а executable migration содержит только
детерминированное преобразование.

### Legacy adoption

Для проекта без metadata migrator сначала строит отчёт:

- предполагаемый профиль;
- найденные расхождения;
- файлы, которыми можно управлять безопасно;
- файлы, требующие ручного решения.

Автоматически назначать профиль по неполному совпадению нельзя.

## Поток 6. Supply-chain и governance

### Изменения в репозитории

- pin сторонних GitHub Actions по полной commit SHA;
- Dependabot для `github-actions`;
- проверка, запрещающая mutable action references;
- рабочий `docs/security/THREAT_MODEL.md` для bootstrap supply chain;
- secret/path scan и contract validator в CI;
- macOS smoke workflow по `workflow_dispatch` и при изменениях shell-слоя.

### Внешние настройки GitHub

После отдельного разрешения пользователя:

- запрет force-push и удаления `main`;
- required CI checks;
- linear history;
- PR requirement хотя бы для `.github/`, `scripts/`, `.agents/`, templates и
  global policy.

Ruleset является внешним consequential action и не должен меняться только на
основании этого плана.

## Поток 7. UX и документация

- одна quick-start страница по командам;
- стабильные exit codes: `0` success, `1` validation failure, `2` usage error;
- `--json` для validator и migration plan после стабилизации human output;
- сообщения всегда разделяют: changed, already correct, skipped, blocked;
- Agent Skills вызывают те же entry points, а не воспроизводят их логику;
- generated project хранит ссылку на свой standard version и migration guide.

## Последовательность реализации

### Этап A. ADR и contract skeleton

1. Утвердить решения из раздела «Требуется выбор».
2. Создать ADR о runtime и формате manifest.
3. Добавить `STANDARD_VERSION` и contract fixtures без изменения bootstrap.
4. Написать contract tests на текущем поведении.

Gate: текущее дерево генерируемых проектов не изменилось.

### Этап B. Manifest-driven bootstrap

1. Перевести profile composition и index relationships в manifest.
2. Оставить thin native adapters.
3. Сравнить generated snapshots до и после рефакторинга.
4. Добавить metadata только после parity gate.

Gate: shell и PowerShell создают идентичные профили.

### Этап C. Validator и doctor

1. Реализовать read-only checks.
2. Подключить их к CI.
3. Добавить human-readable и стабильные exit codes.
4. Проверить на текущем repo и representative generated projects.

Gate: validator не исправляет файлы и не выдаёт ложных ошибок на поддерживаемых
профилях.

### Этап D. Global sync

1. Ввести managed-block parser.
2. Реализовать `check` и `diff`.
3. Подключить states к doctor, skills и CI без mutation.
4. Передать backup, подтверждаемый `apply` и миграцию текущего компьютера в
   общую migration infrastructure Этапа E.

Gate: пользовательский текст вне managed block побайтно сохранён.

### Этап E. Migration engine

1. Реализовать read-only legacy inspection и migration plan. — completed
2. Добавить metadata и global marker adoption contracts. — completed
3. Ввести clean-tree preconditions, no-mutation и idempotent plan tests. — completed
4. Реализовать fingerprint-protected atomic backup/write и разрешить явный
   `--apply`. — completed

Gate: все изменения представлены как reviewable git diff.

### Этап F. Supply-chain hardening

1. Pin Actions, добавить Dependabot и threat model. — completed
2. Добавить macOS smoke workflow. — completed
3. Применить GitHub ruleset. — blocked внешним GitHub plan для private repo;
   API evidence записан в [[ACTIONS]].

Gate: protected `main` принимает обновления зависимостей без отключения
обязательных проверок.

## Требуется выбор

| Решение | Рекомендация | Альтернатива | Цена выбора |
|---|---|---|---|
| Contract format | TSV | JSON/YAML | TSV проще для native shell; JSON удобнее Python, YAML требует parser |
| Advanced runtime | Python 3 stdlib | дублировать sh/PowerShell | Python уменьшает расхождение validator/migrator, но становится дополнительным tool |
| Global ownership | managed block | владеть всем файлом | managed block сохраняет локальные правила, но требует marker migration |
| Migration default | plan-only | auto-apply | plan-only безопаснее, но требует дополнительной команды |
| Project metadata | `.project-standard.json` | frontmatter `PROJECT.md` | отдельный JSON машиночитаем и не смешивает human content |
| macOS CI | manual + path-triggered | каждый push | снижает расходы, но не проверяет Markdown-only commits |
| Main governance | PR для критичных путей | прямой push всегда | PR снижает bootstrap supply-chain risk, но замедляет маленькие изменения |

## Риски

- Manifest может стать вторым источником истины, если scripts продолжат
  содержать собственные profile lists.
- Managed markers могут конфликтовать с вручную изменённым global file.
- Validator может превратиться в жёсткий formatter и мешать проектной свободе;
  поэтому contract должен проверять invariants, а не стиль текста.
- Migration engine опасен без clean-tree guard, idempotence и reviewable diff.
- Python dependency нельзя вводить скрыто или использовать для базового
  bootstrap до явного решения.
- GitHub ruleset может заблокировать привычный direct-push workflow; внешнее
  изменение требует отдельного подтверждения.

## Non-goals

- синхронизация сырых Codex или Claude memory;
- централизованное хранение знаний всех проектов;
- автоматическое исправление бизнес-документации;
- обязательный monorepo;
- скрытая установка runtimes или GitHub configuration;
- миграция существующих проектов без preview и согласия пользователя.

## Definition of Done стратегического этапа

- один machine-readable contract управляет профилями и проверками;
- каждый новый проект знает schema version и provenance;
- validator read-only и одинаково работает на Windows/macOS/Linux;
- global sync обнаруживает drift и безопасно сохраняет локальные дополнения;
- legacy migration сначала строит план и создаёт reviewable git diff;
- CI проверяет contract, secrets, paths, skills и обе платформенные реализации;
- threat model описывает bootstrap, global instructions, skills, memory
  promotion и GitHub publication;
- документация и Agent Skills вызывают реальную автоматизацию, не дублируя её.

## Следующий implementation batch

Этапы A–E завершены. Global adoption выполняется только после reviewed
fingerprint; project adoption будет применяться при создании новых проектов или
к отдельно выбранному legacy repository. На основном компьютере global marker
adoption выполнен 2026-06-30 с точным backup и postcondition `managed_match`;
evidence хранится в [[ACTIONS]].

Стратегические этапы A–F реализованы в пределах доступных возможностей
repository и GitHub plan. Единственный внешний gap — ruleset/branch protection
для private repo. После перехода на GitHub Pro либо изменения visibility нужно:

1. запретить deletion и force-push `main`;
2. потребовать linear history и успешные `ci`/`macos-smoke` checks для core
   changes;
3. согласовать переход критичных путей на PR workflow;
4. записать ruleset ID и rollback в [[ACTIONS]].
