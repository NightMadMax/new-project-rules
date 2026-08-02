---
type: architecture
status: active
owner: project
last_verified: 2026-07-26
source_of_truth: repository
related:
  - "[[docs/architecture/decisions/ADR-0002-versioned-project-contract|ADR-0002]]"
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN]]"
  - "[[docs/guides/PLAN_MIGRATIONS]]"
---

# Project standard metadata schema

`.project-standard.json` фиксирует применённую schema, профиль и provenance
стандарта. Это машиночитаемый state migrator, а не описание проекта.

Текущая schema `5`:

```json
{
  "schema_version": 5,
  "profile": "software",
  "capabilities": ["jira-confluence"],
  "capability_releases": {},
  "source": "NightMadMax/new-project-rules",
  "source_commit": "<40-hex-commit>",
  "created_at": null,
  "adopted_at": "YYYY-MM-DD",
  "applied_migrations": [
    "0001-adopt-project-standard",
    "0004-upgrade-project-standard-v2",
    "0007-upgrade-project-standard-v3",
    "0010-upgrade-project-standard-v4",
    "0013-upgrade-project-standard-v5"
  ]
}
```

## Инварианты

- `schema_version` — положительное целое, не release version.
- `profile` — `minimal`, `software`, `operated` или `all`.
- `capabilities` — независимые от профиля подключаемые возможности. Сейчас поддерживаются
  `jira-confluence`, `1c` и `transcribe`; пустой массив означает, что
  capability не
  выбрана. Возможности дополняют профиль и не меняют его состав.
- `capability_releases` — установленные release capability: ключ равен ID
  capability из `capabilities`, значение содержит только `version` (SemVer) и
  `release_id` (64-hex digest канонических файлов release). Пустой объект
  означает, что ни одна capability не поставила свой release. Версия capability
  и schema стандарта — независимые оси: release не участвует в цепочке
  миграций, он сравнивается по `release_id`.
- Schema 5 добавляет `capability_releases`.
- Schema 4 фиксирует трёхуровневый контракт инструкций агента; формат metadata
  относительно schema 3 не меняется, но sequential history подтверждает
  применение обновлённого global/project policy contract.
- `source` берётся из `config/standard-source.txt`, а `source_commit` — из
  проверенного commit репозитория правил; локальный путь и remote с credentials
  не записываются.
- Для нового проекта `created_at` содержит дату bootstrap. При adoption legacy
  проекта она равна `null`, потому что migrator не выдумывает историческую дату.
- `adopted_at` фиксирует дату adoption, а `applied_migrations` — уникальные ID
  уже применённых преобразований.
- Metadata не содержит токены, имя компьютера или абсолютные пути.

## Ledger `.project-standard-artifacts.json`

Отдельный файл рядом с metadata: metadata отвечает на вопрос «какая схема и
версия», ledger — «какие файлы поставлены и в каком состоянии оставлены».
Схема ledger нумеруется независимо; текущая — `1`.

```json
{
  "schema_version": 1,
  "artifacts": [
    {
      "target": "config/1c-mcp-catalog.json",
      "owner": "capability:1c",
      "policy": "managed",
      "payload_class": "verbatim",
      "hash": "sha256:<64 hex>"
    }
  ]
}
```

- `target` — repo-relative путь без `..`, абсолютных путей и обратных слэшей.
- `owner` — `standard` или `capability:<id>`.
- `policy` — `managed` (обновляется миграцией с проверкой предыдущего
  состояния), `seed` (создаётся один раз и дальше принадлежит пользователю) или
  `owned-block` (в смешанном файле принадлежит только блок или набор ключей).
- `payload_class` — как артефакт доставляется: `template`, `verbatim`, `binary`
  или `owned-block`; классы `owned-block` в policy и payload_class всегда
  совпадают.
- `hash` — `sha256:<64 hex>` для managed и owned-block; для `seed` всегда
  `null`, иначе правка пользователя читалась бы как дрейф. Для `owned-block`
  hash считается по принадлежащему capability блоку, а не по файлу целиком.
- Записи уникальны по `target` и отсортированы по нему: обновление должно давать
  читаемый детерминированный diff.
- В ledger не попадают машинные пути, порты, доступность CLI и локальное
  состояние; версия capability живёт в `.project-standard.json`, а не здесь.

Изменение схемы ledger — такая же строка в `config/migrations.tsv`, как и
изменение metadata.

## Три реестра артефактов и направление данных

Реестра три, и они отвечают на разные вопросы. Путать их дорого: один и тот же
файл иначе получит двух владельцев.

| Реестр | Вопрос | Живёт |
|---|---|---|
| `config/1c-artifacts.tsv` | Что вообще входит в release и откуда взято | Только в репозитории стандарта; в проект не копируется |
| `config/capabilities.tsv` | Что и как доставлять в проект | Репозиторий стандарта |
| `.project-standard-artifacts.json` | Что фактически установлено и в каком состоянии оставлено | Созданный проект |

Направление данных одностороннее: build-time inventory → манифест доставки →
ledger проекта. Строки манифеста доставки для capability пишутся вручную и
проверяются против inventory при сборке release; ledger проекта не пишет никто,
кроме транзакции доставки. Обратного потока нет: ledger никогда не меняет
манифест, а манифест — inventory.

Поля не пересекаются по смыслу. `ownership` в build-time inventory
(`project-managed`, `project-seed`, `provider-only`, `pinned-external`) отвечает
на вопрос «попадает ли файл в проект вообще». `policy` в манифесте доставки
(`managed`, `seed`) — «обновляем ли мы его после установки». `payload_class` —
«как переносим байты».

Migration manifest `config/migrations.tsv` является источником истины для ID,
target, перехода schema и handler. Legacy state обозначается schema `0`.
Planner строит единственную последовательную цепочку до текущей schema;
пропущенный или неоднозначный переход блокирует запись.
