---
type: quality-report
status: active
owner: project
last_verified: 2026-07-30
source_of_truth: repository
related:
  - "[[docs/architecture/ONE_C_CAPABILITY_PLAN]]"
  - "[[docs/architecture/one-c/IMPLEMENTATION_PLAN]]"
  - "[[docs/quality/TESTING]]"
  - "[[docs/quality/DEFECTS]]"
---

# Готовность capability `1c`

Что из принятых критериев готовности действительно проверяется, чем именно, и
что ещё нет. Строка на каждый критерий раздела «Критерии готовности»
[[docs/architecture/ONE_C_CAPABILITY_PLAN|мастер-плана]]; порядок и нумерация —
его.

Матрица проверяется машинно: `scripts/test-1c-readiness.py` сверяет её с
мастер-планом и падает, если критерий остался без строки или переформулирован,
статус `тест` указывает на файл, которого нет или который не запускается в CI, а
`не выполнено` — на дефект, которого нет в открытых. Без этой проверки такая
таблица через месяц описывает прошлое.

Статус `частично` существует, потому что без него картина искажается в обе
стороны: критерий, закрытый наполовину, выглядел бы выполненным, а критерий, у
которого проверена половина, — невыполненным.

## Статусы

| Статус | Что означает |
|---|---|
| `тест` | Проверяется автоматически. Доказательство — имя теста. |
| `Windows` | Требует runtime 1С; проверяется на Windows-сессии, [[docs/architecture/one-c/IMPLEMENTATION_PLAN\|веха W]]. |
| `частично` | Часть критерия проверяется, часть нет. Доказательства — тест **и** номер дефекта. |
| `не выполнено` | Не поставлено. Доказательство — номер дефекта. |
| `отложено` | Отложено решением плана, дефектом не считается. Доказательство — номер решения. |

## Матрица

| # | Критерий | Статус | Доказательство |
|---|---|---|---|
| 1 | Проект создаётся с `1c` отдельно и вместе с `jira-confluence` | тест | `scripts/test-preset-core.py` |
| 2 | Ядро preset защищено машинно | тест | `scripts/test-preset-core.py` |
| 3 | Снятие ядра capability невозможно | тест | `scripts/test-preset-core.py`, `scripts/test-migration-planner.py` |
| 4 | Базы не ограничены портами; до десяти на `6003`–`6012` | тест | `scripts/test-one-c-scaffold.py` |
| 5 | Каждый tracked-файл upstream имеет строку ledger | тест | `scripts/test-1c-upstream-routing.py` |
| 6 | Release и миграция доставляют managed, сохраняют seed, ловят drift | тест | `scripts/test-capability-artifacts.py` |
| 7 | Режим `analysis`: read-only сборка на `ordinary`, подтверждённый переключатель записи на `managed` | отложено | решение 1.16 |
| 8 | Live-base skill отказывается без session lock | тест | `scripts/test-1c-session.py` |
| 9 | Fixture write без базы и подтверждения отказывает | тест | `scripts/test-1c-session.py` |
| 10 | Required/conditional/optional разделены и названы в документации | тест | `scripts/test-1c-setup.py`, `scripts/test-1c-readiness.py` |
| 11 | `setup-1c-environment` предлагает компоненты и не ломает репозиторий | тест | `scripts/test-1c-setup.py` |
| 12 | Prompt каталога компонентов содержит обязательные поля | тест | `scripts/test-1c-setup.py` |
| 13 | Отчёт `doctor-1c` содержит назначение, последствия отказа и источник недостающего компонента | тест | `scripts/test-1c-doctor.py` |
| 14 | `doctor-1c` читает только allowlist и маскирует значения | тест | `scripts/test-1c-doctor.py` |
| 15 | Docker provider обнаруживается как внешний deployment | тест | `scripts/test-1c-provider.py` |
| 16 | Templates, scripts и docs не содержат токенов, ключей, строк соединения, машинных путей и названий рабочих баз | частично | `scripts/test-no-secrets.py`, №179 |
| 17 | Плагин и server-vs-client guard требуются только для `ordinary` | тест | `scripts/test-1c-doctor.py` |
| 18 | На не-Windows работают bootstrap, Git, документация и валидаторы | частично | `scripts/test-one-c-scaffold.py`, №180 |
| 19 | `doctor-1c` возвращает версии EDT, патчей и профилей | тест | `scripts/test-1c-doctor.py` |
| 20 | `approved-write` невозможен без backup и non-prod | тест | `scripts/test-1c-session.py` |
| 21 | Scoped `AGENTS.md` содержит правила 1.20, 1.28, evidence | тест | `scripts/test-one-c-scaffold.py` |
| 22 | 13 ролей и 13 upstream-команд в согласованных проекциях | тест | `scripts/test-one-c-scaffold.py` |
| 23 | Второй AI-клиент подключается без re-bootstrap | тест | `scripts/test-1c-clients.py` |
| 24 | Companion-файлы создаются как seed и видны обоим клиентам | тест | `scripts/test-capability-artifacts.py` |
| 25 | OpenSpec поставлен с четырьмя workflow | тест | `scripts/test-one-c-scaffold.py` |
| 26 | Цепочка инструкций измеряется и укладывается в 32 КиБ | тест | `scripts/test-one-c-scaffold.py` |
| 27 | Внешние ссылки каталога проверяются report-only и по расписанию | тест | `scripts/test-1c-readiness.py` |
| 28 | Release блокируется, пока в `practices/1c` нет практики `accepted` с evidence | тест | `scripts/test-release-manifest.py` |
| 29 | Реестр несёт `support_mode` и `source_format`; версия БСП записана | частично | `scripts/test-one-c-scaffold.py`, №175 |
| 30 | `deploy-and-test-1c` возвращает отчёт YAxUnit | не выполнено | №199 |
| 31 | Отказы «вне scope v1» названы в пользовательской документации | тест | `scripts/test-1c-readiness.py` |

## Итог

Из 31 критерия: `тест` — 26, `частично` — 3, `Windows` — 0, `не выполнено` — 1, `отложено` — 1.
Счёт сверяется с таблицей машинно: цифра в итоге — это то место, где такой
документ врёт первым.

Не выполненное и половины — это четыре причины:

- **№199 — нет разбора отчёта YAxUnit** (критерий 30). Загрузку исходников
  теперь выполняют доставленные скрипты `db-load-*.ps1` (№165 закрыт), но
  прогон тестов исполнителя не имеет: YAxUnit — условная зависимость, которую
  capability не устанавливает.
- **№175 — версия БСП нигде не хранится** (критерий 29): реестр проверяется
  тестом, карточки `PROJECT_1C.md` из решения 1.20 в поставке нет.
- **№179, №180** — сканер не знает имён рабочих баз (16), блокировка runtime
  на не-Windows не проверяется (18).

Дефект №173 закрыт 2026-07-31: семь критериев (10, 11, 12, 15, 17, 19, 20)
получили исполнителей — каталог компонентов `config/1c-components.tsv` с
prompt из обязательных полей, `scripts/one_c_setup.py`, обнаружение внешнего
provider `scripts/one_c_provider.py`, версии и профили в
`scripts/one_c_doctor.py`, предусловие backup в `scripts/one_c_session.py`.
Веха W показала, что эти критерии ждали не Windows-машину, а исполнителя, и
это подтвердилось: все семь проверяются на любой ОС.

Статус `Windows` не стоит ни у одного критерия. Веха W выполнена
([[docs/quality/RUNTIME_SMOKE_1C|runtime smoke]]): дефекты №61, №137 и №166
закрыты на живой установке. Критерий 7 не ждал и доставки: upstream не содержит
ни одной обработки, а пересборка обработки Toolkit для `managed` отложена
решением 1.16 — поэтому у него статус `отложено`, а не номер дефекта (№198).
