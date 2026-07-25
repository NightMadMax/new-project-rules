---
type: implementation-subplan
status: accepted
owner: project
last_verified: 2026-07-26
source_of_truth: repository
related:
  - "[[docs/architecture/ONE_C_CAPABILITY_PLAN]]"
  - "[[docs/architecture/PROJECT_STANDARD_SCHEMA]]"
  - "[[docs/architecture/decisions/ADR-0002-versioned-project-contract]]"
---

# Capability `1c`: доставка артефактов и состояние проекта

Подплан мастер-плана [[docs/architecture/ONE_C_CAPABILITY_PLAN|capability `1c`]].
Закрывает дефекты №122–№129: механизмы, на которых держится вся поставка
capability, но которых в стандарте сегодня нет.

**Статус — принят** 2026-07-26 вместе с мастер-планом. Разделы ниже — контракт
реализации: код по ним ещё не написан, дефекты №122–№129 остаются открытыми до
его появления.

## Почему один подплан, а не два

Ledger, обработчик миграции, версии и bump схемы правят один и тот же набор
файлов: `config/capabilities.tsv`, `config/migrations.tsv`,
`scripts/plan_migration.py`, `scripts/project_metadata.py`, оба bootstrap-скрипта
и документ схемы. Разводить их по отдельным подпланам — гарантированный конфликт
решений.

## 1. Классы payload и манифест доставки

Сегодня `config/capabilities.tsv` описывает ровно один сценарий: один текстовый
шаблон → один файл назначения с подстановкой имени проекта. Capability `1c`
требует ещё трёх (дефект №124).

| Класс | Что это | Как доставляется |
|---|---|---|
| `template` | Текущий сценарий: Markdown-шаблон с плейсхолдерами | Подстановка, как сейчас |
| `verbatim` | Побайтный файл vendored subtree | Копирование без подстановки, hash обязан совпасть с source |
| `binary` | EPF и другие двоичные артефакты | Копирование в бинарном режиме, никаких текстовых преобразований |
| `template` (runtime) | Шаблоны профилей `.launch`: поставляются при bootstrap, инстанцируются `add-1c-base` | Шаблон managed и в ledger; созданный профиль базы user-owned и вне ledger |
| `owned-block` | Смешанный файл (`.mcp.json`, `.claude/settings.json`, `.codex/config.toml`, `.gitattributes`, `.gitignore`) | Правится только принадлежащий capability блок/ключ |

Решения:

1. В манифест добавляется колонка `payload_class`; отсутствующее значение
   означает `template`, поэтому существующие строки `jira-confluence` не
   меняются.
2. Каталоги в манифесте **не вводятся**. Vendored subtree разворачивается в
   строки ledger на build-time: 91 файл skill — это 91 запись в
   `config/1c-artifacts.tsv`, а манифест ссылается на subtree одной строкой
   класса `verbatim` с корнем и ожидаемым составом. Это сохраняет правило «одна
   строка = один проверяемый объект» и не заводит второй формат обхода.
3. `sed`-подстановка применяется только к `template`. Для остальных классов
   bootstrap обязан использовать побайтное копирование; parity shell/PowerShell
   проверяется тестом.

## 2. Обработчик `capability_artifacts`

Сегодня `scripts/plan_migration.py` знает три обработчика, работает с одним
`destination` и одним текстовым `atomic_write` (дефект №122). Контракт нового
обработчика:

- **План.** Строит полный список операций `(target, payload_class, action,
  installed_hash, desired_hash, owner)` без единой записи на диск. `action` —
  `create`, `update`, `remove` или `skip`.
- **Дрейф.** Если фактический hash target не совпадает с installed hash из
  ledger, операция помечается конфликтом и вся транзакция останавливается.
  Молчаливая перезапись запрещена.
- **Атомарность.** Все файлы пишутся во временные, затем переименовываются;
  отказ любой операции откатывает всю цепочку. Частично применённая миграция —
  недопустимое состояние.
- **Удаление.** Managed target удаляется только при совпадении current и
  installed hash. Project-seed и user-owned файлы не удаляются никогда;
  непустые каталоги сохраняются.
- **Seed.** Класс project-seed создаётся только при отсутствии и после этого
  не сравнивается по hash.
- **Согласование с движком.** Обработчик подчиняется существующим правилам:
  `--plan`/`--apply`, обязательный `--yes`, проверка fingerprint.

## 3. Ledger `.project-standard-artifacts.json`

Сегодня файла нет нигде, кроме текста мастер-плана (дефект №123). Предлагаемый
контракт:

```json
{
  "schema": 1,
  "artifacts": [
    {
      "target": "config/1c-mcp-catalog.json",
      "owner": "capability:1c",
      "policy": "managed",
      "payload_class": "verbatim",
      "hash": "sha256:…"
    }
  ]
}
```

- `policy` — `managed`, `seed` или `owned-block`.
- Для `owned-block` hash считается **не от файла**, а от нормализованного
  содержимого принадлежащего capability блока или набора ключей: иначе любая
  пользовательская правка соседней строки читалась бы как дрейф.
- Версия capability и `release_id` в ledger не дублируются: они живут в
  `.project-standard.json`, ledger отвечает только за файлы.
- Побайтный subtree занимает одну строку с агрегатным hash; пофайловый
  inventory остаётся build-time артефактом.
- Ledger описывает только стабильные Git-артефакты. Машинные пути, порты,
  доступность CLI и локальное состояние в него не попадают.
- У ledger собственная `schema`, и её изменение — такая же строка в
  `config/migrations.tsv`, как и изменение metadata.
- Владелец схемы — документ [[docs/architecture/PROJECT_STANDARD_SCHEMA]],
  раздел про ledger; валидатор — отдельный модуль по образцу
  `scripts/project_metadata.py`.

## 4. Версии: SemVer capability против schema-цепочки

Движок миграций знает только целочисленные переходы `from_schema → to_schema`
и требует ровно одну миграцию на переход; `applied_migrations` обязан совпадать
с детерминированным путём (дефект №125).

Решение: **это две независимые оси, и смешивать их не нужно.**

- Schema стандарта остаётся целочисленной и описывает формат metadata и ledger.
- Версия capability (SemVer + `release_id`) хранится как значение внутри
  metadata/ledger, а не как звено schema-цепочки.
- Обновление capability — миграция с обработчиком `capability_artifacts`,
  чей план строится сравнением installed `release_id` с published. Пропуск
  нескольких версий допустим, потому что план строится по фактическому
  состоянию файлов, а не по цепочке промежуточных шагов.
- Downgrade не поддерживается: дефектный release исправляется forward patch.

## 5. Bump схемы metadata до 5

Запись release в `.project-standard.json` и capability `1c` в `CAPABILITY_NAMES`
меняют формат metadata, а этого в этапах мастер-плана нет (дефект №128). Состав
работы:

1. `STANDARD_VERSION` 4 → 5.
2. Строки `config/migrations.tsv` для существующих targets по действующему
   образцу.
3. `CAPABILITY_NAMES` дополняется `1c`; guards обоих bootstrap-скриптов
   перестают быть однокапабилитными.
4. [[docs/architecture/PROJECT_STANDARD_SCHEMA]] описывает новые поля и ledger.
5. Тест: проект schema 4 обновляется до 5 без потери `applied_migrations`.

## 6. Ядро preset и Best Practices

Два связанных дефекта: порядок шагов (№126) и природа манифеста (№127).

- **Порядок.** Для preset `1c` шаг Best Practices выполняется **до** валидации,
  а не после: иначе обязательная проверка ядра падает на только что созданном
  проекте. Для preset `1c` выбор стека `1c` безусловен.
- **Признак стека.** `.best-practices.json` хранит preferences `ask`/`optout`,
  поэтому «наличие секции» ничего не доказывает. Машинный признак ядра —
  `sections["1c"] != "optout"`, и `validate-project.py` начинает читать этот
  файл (сейчас не читает вовсе).
- **Пустой стек.** `practices/1c` в соседней базе Best Practices содержит только
  заглушку. Обязательность стека до первого release остаётся **структурной**:
  проверяется подключение секции, а не число практик. Наполнение стека —
  условие первого release capability, а не условие создания проекта
  (решение 1.29: минимум одна принятая практика с evidence).

## 7. Проверки skills

`scripts/test-skills.sh` хардкодит девять имён и требует триаду
`SKILL.md` + `.claude`-мост + `agents/openai.yaml` (дефект №129). Нужны:

- обход по манифесту вместо списка имён, включая capability-скиллы, которые
  сегодня не покрыты ни одной проверкой;
- отдельный класс проверки vendored payload: совпадение hash и отсутствие
  локальных правок, **без** требования внутреннего `agents/openai.yaml` —
  discovery metadata и мост живут снаружи subtree;
- parity `test-skills.sh` и `test-skills.ps1`.

## 8. Порядок работ

1. Ledger и bump схемы (разделы 3 и 5) — от них зависит всё остальное.
2. Классы payload и манифест (раздел 1).
3. Обработчик `capability_artifacts` (раздел 2) и версии (раздел 4).
4. Порядок preset/Best Practices (раздел 6).
5. Проверки skills (раздел 7) — независимы, можно раньше.

## 9. Закрытые развилки

Решены 2026-07-26, отдельного пересмотра не требуют:

- **Версия capability.** `.project-standard.json` хранит краткую запись —
  версию и `release_id`; ledger хранит только артефакты и их hash. Планировщик
  миграций читает версию там же, где профиль и список capability, и не
  разбирает файловый реестр ради одного значения.
- **Шаблоны профилей запуска.** Сам `.launch`-шаблон — обычный `template`
  класса managed и попадает в ledger. Профиль конкретной базы, который
  инстанцирует `add-1c-base`, машинозависим, принадлежит пользователю и в
  ledger **не попадает**; drift-check его не проверяет.
- **Проверка vendored subtree.** В ledger проекта — одна строка на subtree с
  агрегатным hash. Полный пофайловый inventory живёт в build-time
  `config/1c-artifacts.tsv`. При расхождении агрегата `doctor-1c` пересчитывает
  пофайлово по release payload и называет конкретный разошедшийся файл.
