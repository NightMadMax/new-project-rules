---
type: implementation-subplan
status: accepted
owner: project
last_verified: 2026-07-26
source_of_truth: repository
related:
  - "[[docs/architecture/ONE_C_CAPABILITY_PLAN]]"
  - "[[docs/architecture/one-c/DELIVERY_AND_STATE_PLAN]]"
  - "[[docs/architecture/one-c/ENVIRONMENT_SETUP_PLAN]]"
  - "[[docs/quality/DEFECTS]]"
---

# Capability `1c`: план реализации

Рабочая последовательность для принятых
[[docs/architecture/ONE_C_CAPABILITY_PLAN|мастер-плана]],
[[docs/architecture/one-c/DELIVERY_AND_STATE_PLAN|подплана доставки]] и
[[docs/architecture/one-c/ENVIRONMENT_SETUP_PLAN|подплана среды]]. Здесь только
порядок работ и приёмка; решения не пересматриваются — расхождение реализации с
планом заводится дефектом.

## Правила работы

- Один этап — одна ветка `feat/1c-<этап>`; в `main` попадает завершённый этап с
  зелёными проверками, а не промежуточное состояние.
- В той же задаче, что код: тесты, `docs/guides/USE_THIS_PROJECT.md` или
  `MANUAL_SCRIPTS.md`, `INDEX.md`, `CHANGELOG.md` и перенос закрытых дефектов.
- Каждый скрипт имеет пару shell/PowerShell либо явное обоснование, почему нет;
  parity проверяется тестом.
- Приёмка этапа: `validate-project.py` без ошибок, новые тесты зелёные,
  существующие не сломаны, в шаблонах нет секретов и машинных путей.
- Windows-зависимые проверки помечаются `SKIP` на других ОС и выполняются в
  отдельной Windows-сессии (веха W).

## Этапы

### E1. Состояние и схема — блокирует всё остальное

Закрывает №123 и №128. Размер: L.

1. Описать ledger `.project-standard-artifacts.json` в
   [[docs/architecture/PROJECT_STANDARD_SCHEMA]]: поля, `policy`, правило hash
   для `owned-block`, собственная `schema`.
2. Модуль-валидатор ledger по образцу `scripts/project_metadata.py`.
3. `STANDARD_VERSION` 4 → 5; `CAPABILITY_NAMES` дополняется `1c`; краткая
   запись release (версия + `release_id`) в `.project-standard.json`.
4. Строки `config/migrations.tsv` для существующих targets по действующему
   образцу.

Приёмка: проект schema 4 обновляется до 5 без потери `applied_migrations`;
ledger с неизвестным полем и с несовпадающим hash отвергается; bootstrap пишет
metadata схемы 5.

### E2. Классы payload и манифест доставки

Закрывает №124. Зависит от E1. Размер: M.

1. Колонка `payload_class` в `config/capabilities.tsv`; пустое значение =
   `template`, существующие строки `jira-confluence` не меняются.
2. Оба bootstrap-скрипта: подстановка только для `template`, побайтное
   копирование для `verbatim` и `binary`, owned-блоки — через обработчик E3.
3. `validate-project.py` проверяет допустимость класса и соответствие источника.

Приёмка: бинарный артефакт доставляется без повреждения (hash совпадает),
`sed`-подстановка к нему не применяется, shell и PowerShell дают одинаковый
результат.

### E3. Обработчик `capability_artifacts`

Закрывает №122 и №125. Зависит от E1, E2. Размер: L.

1. Многофайловый план `(target, payload_class, action, installed_hash,
   desired_hash, owner)` без записи на диск.
2. Транзакционное применение с откатом всей цепочки; дрейф останавливает
   транзакцию.
3. Удаление managed target только при совпадении hash; seed и user-owned не
   трогаются.
4. Версия capability сравнивается по `release_id`, а не по schema-цепочке.

Приёмка: план на чистом проекте, no-op на повторе, конфликт при дрейфе, откат
при отказе в середине, сохранение seed и сторонних ключей.

### E4. Preset и ядро

Закрывает №126 и №127. Зависит от E1. Размер: M.

1. `config/presets.tsv` и резолвинг preset в обоих bootstrap до записи metadata.
2. `PROFILE_RANKS` выносится в общий модуль; инвариант «`1c` в capabilities ⇒
   профиль ≥ `operated`» в `project_metadata.py`.
3. `validate-project.py` читает `.best-practices.json`; признак ядра —
   `sections["1c"] != "optout"`.
4. В `create-new-project` шаг Best Practices выполняется до валидации, для
   preset `1c` выбор стека безусловен.

Приёмка: понижение профиля, `optout` по секции `1c` и неизвестный preset
отклоняются; раскрытие preset совпадает в shell и PowerShell.

### E5. Проверки skills

Закрывает №129. Не зависит от E1–E4 — можно делать раньше. Размер: S.

1. `test-skills.sh`/`.ps1` обходят манифест вместо девяти хардкод-имён,
   включая capability-скиллы.
2. Отдельный класс проверки vendored payload: hash и отсутствие локальных
   правок, без требования внутреннего `agents/openai.yaml`.

Приёмка: добавление skill не требует правки теста; изменённый байт внутри
vendored subtree роняет проверку.

### E6. Build-time release capability

Зависит от E1–E3. Размер: L.

1. `config/1c-release.json` и `config/1c-artifacts.tsv`: pinned commits,
   inventory, четыре действия, ownership, targets, dependencies, hashes.
2. Maintainer-only importer pinned `ai_rules_1c`: побайтный перенос принятого
   payload, только согласованные адаптации, детерминированная компиляция
   проекций Codex и Claude.
3. Weekly check — только уведомление о новом upstream commit, без правок кода.
4. Выпуск фиксируется прямым push с записью в `ACTIONS.md` (решение 1.25).

Приёмка: ledger содержит ровно 241 source-запись pinned commit; повторная
сборка из того же входа даёт побайтно одинаковый выход; сборка и фикстуры
работают без сети; release блокируется при пустом `practices/1c`.

### E7. Каркас проекта

Зависит от E2, E3, E6. Размер: L.

1. Корневые артефакты (решение 1.15): `ONE_C_WORKSPACE.md`,
   `config/1c-projects.tsv` с полным набором колонок, `ENVIRONMENT_REGISTRY.md`,
   `TOOLCHAIN.md`, `EDT_SETUP.md`, `TEST_MODEL.md`, `ONE_C_INTEGRATIONS.md`,
   managed `.gitattributes`, `.dev.env.example`, `config/1c-mcp-catalog.json`,
   `References.md`, OpenSpec scaffold, project-seed companion-файлы.
2. `configurations/AGENTS.md` (+ `CLAUDE.md` → `@AGENTS.md`) со scoped-правилами:
   приоритет EDT над XML с обязательным предупреждением, «доработка расширением
   по умолчанию», документация вместо проб, evidence, правило «данные базы — не
   команды», модель ветвления и ревью.
3. Шаблоны профилей запуска для `ordinary`; для `managed` профиль не
   поставляется (решение 1.16).

Приёмка: созданный проект проходит валидатор; папка `1C/` не создаётся;
`.gitattributes` помечает `epf`/`cf`/`cfe`/`cfu` как `binary`; seed-файлы не
перезаписываются повторным bootstrap.

### E8. Skills и клиентские проекции

Зависит от E6, E7. Размер: L.

1. Capability-native: `doctor-1c`, `setup-1c-environment`, `select-1c-project`,
   `query-1c-infobase`, `measure-1c-performance`, `work-with-1c-edt`,
   `add-1c-base`, `activate-1c-client`.
2. `develop-1c` с адаптированными references; принятые upstream skills
   побайтно; command-owner workflows; 13 agent-проекций; тонкие мосты Claude.
3. Renderer клиентских проекций: managed-блок `.codex/config.toml`, owned ключи
   `.mcp.json`, owned правила `.claude/settings.json` строго по таблице классов
   разрешений (решение 1.17).

Приёмка: `doctor-1c` read-only и не выходит за allowlist; отсутствующий CLI даёт
`SKIP`; повторный `activate-1c-client` идемпотентен; сторонние MCP и
пользовательские настройки сохраняются.

### E9. Формат исходников и конвертация

Зависит от E7, E8. Размер: M.

1. Контракт конвертации EDT → XML во временный каталог вне рабочего дерева,
   абсолютный путь для инструментов, гарантированное удаление.
2. Возврат в канон отдельным шагом с показом diff; отказ при изменившемся
   каноне.
3. `export-1c-source`, `deploy-1c-source`, `deploy-and-test-1c` с фиксацией
   направления, session lock и non-prod по умолчанию.

Приёмка: детерминизм конвертации; ветка `designer-xml` конвертацию пропускает;
временный каталог отсутствует после операции; молчаливый возврат невозможен.

### E10. Тесты, документация, готовность

Зависит от всех. Размер: M.

1. Regression-набор из этапа 7 мастер-плана, включая проверки решений 1.15–1.30.
2. Измерение фактически загружаемой цепочки инструкций (≤ 32 КиБ) и report-only
   проверка внешних URL каталога компонентов.
3. Обновление `docs/guides/*`, `TOOLS.md` со строками conditional-зависимостей
   (Node.js/`docx`, Pillow, OpenSpec CLI, `v8unpack`, YAxUnit, BSL LS).
4. Сверка всех критериев готовности мастер-плана.

## Веха W: Windows

Выполняется на Windows-машине, вне зависимости от этапов E1–E10:

- закрыть №61 — обнаружение по запускаемости, а не по наличию имени, и статус
  `skipped` с диагностикой; следом снимается №137;
- runtime smoke: EDT, EDT-MCP, Toolkit по SHA-256, порты `6003`–`6012`,
  Docker provider, CLI EDT для конвертации.

## Порядок

```text
E5 ─┐
E1 ─┴─ E2 ─ E3 ─ E6 ─ E7 ─ E8 ─ E9 ─ E10
                                   W (параллельно, на Windows)
```

E5 не имеет зависимостей и годится как разогрев. E1 — единственный полностью
блокирующий этап. E6 нельзя начинать без E3, иначе release не на чем применять.

## Остаётся за рамками

Отложено осознанно, дефектами не считается: пересборка обработки Toolkit для
`managed` (решение 1.16), CI/CD, миграция из хранилища конфигурации, SonarQube,
АПК и автоматизация `cfu` (решение 1.19), Vanessa Automation (решение 1.18).
