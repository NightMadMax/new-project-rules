---
type: research
status: proposed
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/research/NPR_BP_HARVEST_ANALYSIS_2026-07-07]]"
  - "[[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture]]"
  - "[[docs/quality/DEFECTS]]"
---

# План исправления связки NPR и Best Practices

## Цель

Довести связку `new-project-rules` (NPR) и `Best Practices` (BP) до состояния,
в котором оба опубликованных `main` защищены, совместимы, автоматически
проверяют общий knowledge lifecycle и дают измеримую пользу consumer projects.

Основание: [[docs/research/NPR_BP_HARVEST_ANALYSIS_2026-07-07|совместный harvest-анализ]].

## Правила выполнения

- Исправлять по фазам; не смешивать GitHub governance, cross-repo contract и
  наполнение базы в один PR.
- Не выполнять PR, ruleset и release операции без отдельного подтверждения
  пользователя, как требуют repository rules.
- После каждого изменения запускать локальный suite соответствующего
  репозитория и дождаться обязательного GitHub CI.
- Не закрывать дефект до проверки фактического postcondition, а не только
  изменения документации.
- Не запускать двух агентов одновременно в одной рабочей копии; параллельная
  работа допустима только в отдельных worktrees.

## Последовательность

```text
Фаза 0: согласование внешних действий
  ├─ Фаза 1: опубликовать BP hardening
  ├─ Фаза 2: защитить NPR main
  └─ Фаза 3: убрать stale route
             ↓
       Фаза 4: cross-repo contract
             ↓
       Фаза 5: версия и release NPR
             ↓
       Фаза 6: наполнить BP
             ↓
       Фаза 7: consumer pilot и метрики
```

## Фаза 0. Согласовать внешние изменения

### Решения пользователя

1. Разрешить создать PR `codex/p1-trust-hardening → main` в BP.
2. Согласовать параметры ruleset для `new-project-rules/main`.
3. Согласовать номер новой версии NPR после анализа migration contract.
4. Назвать минимум два consumer projects для пилота BP.

### Выход

- Зафиксированный scope внешних действий.
- Ни один GitHub setting, PR или release до этого gate не изменён.

## Фаза 1. Доставить BP hardening в `main`

### Действия

1. Обновить feature branch от `origin/main` и проверить diff всех коммитов.
2. Запустить `make check` и отдельно проверить отсутствие secrets/path leaks.
3. Создать один reviewable PR с перечнем lifecycle, validator, catalog и metrics
   изменений.
4. Дождаться `Validate`, approval, Code Owner review и разрешения всех threads.
5. Merge выполнить штатным способом, затем обновить локальный `main` и повторно
   запустить `make check` именно на merge commit.

### Критерии готовности

- `origin/main` содержит hardening commits.
- Feature branch не является единственным источником новых возможностей.
- `gh pr list --state open` не показывает незавершённый hardening PR.
- Дефект BP «P1 hardening не интегрирован в main» перенесён в `Fixed` с PR и
  merge commit.

## Фаза 2. Защитить `new-project-rules/main`

### Предлагаемый минимальный ruleset

- target: default branch `main`;
- require pull request before merging;
- минимум один approval;
- require Code Owner review для governance/skills/workflows;
- require conversation resolution;
- required checks: `ci` и `macos-smoke` с учётом path-trigger semantics;
- block deletion и non-fast-forward updates;
- bypass только для явно согласованных maintainer/emergency ролей.

### Действия

1. Сопоставить параметры с действующим ruleset BP.
2. Показать пользователю точный JSON/настройки до применения.
3. После подтверждения создать ruleset через GitHub API.
4. Повторно прочитать ruleset и проверить `main.protected=true`.
5. По возможности выполнить безопасную negative verification: убедиться, что
   правила требуют PR/checks, не делая пробный прямой push.

### Критерии готовности

- GitHub API возвращает active ruleset для `main`.
- Required checks соответствуют реально существующим workflow/check names.
- Дефект NPR №48 перемещён в `Fixed` с ruleset ID и датой проверки.

## Фаза 3. Исправить устаревший knowledge route в BP

### Действия

1. Удалить ссылки на `harvest-project-lessons` из `README.md`,
   `harvest-practice-candidates/SKILL.md` и других найденных документов.
2. Зафиксировать один маршрут:
   `harvest-practice-candidates → review-practice-candidates → accepted practice`;
   дальнейшее затвердевание в NPR выполняет только maintainer через
   `promote-project-knowledge → apply-promotion-candidate`.
3. Обновить Claude bridge только если меняется canonical skill metadata.
4. Добавить локальный repository-contract test, запрещающий удалённое имя skill.

### Проверки

```sh
rg -n "harvest-project-lessons" README.md docs .agents .claude
make check
```

Первый вызов должен завершиться без совпадений.

### Критерии готовности

- Пользовательские и skill-инструкции согласованы с ADR-0003.
- Regression test ловит повторное появление stale route.
- Соответствующий дефект BP перемещён в `Fixed` с commit/PR.

## Фаза 4. Ввести исполняемый cross-repository contract

### Решение по архитектуре

Не связывать CI с обязательным сетевым клонированием соседнего репозитория:
это делает тесты нестабильными и мешает воспроизводимости. Ввести два слоя:

1. **Checked-in compatibility manifest** в NPR с минимальным контрактом:
   repository identity, supported contract schema, обязательные BP skills,
   допустимые practice statuses и provenance requirements.
2. **Pinned integration fixture/test**, который проверяет manifest против
   конкретного BP commit. Обновление pin — отдельный reviewable change.

### Покрываемые инварианты

- обязательные BP skills существуют;
- NPR не ссылается на удалённые BP entry points;
- promotion принимает только существующую `accepted` practice;
- source содержит repository, practice path и полный commit SHA;
- commit содержит неизменённый practice-файл;
- contract schema/version поддерживается обеими сторонами;
- cross-cutting ссылки не копируют rationale в NPR.

### Реализация

1. Добавить manifest/schema и validator в NPR.
2. Добавить fixture с минимальным BP repository snapshot или детерминированный
   checkout helper без runtime network dependency.
3. Подключить suite к `ci` и `macos-smoke` при изменениях knowledge artifacts.
4. Добавить negative fixtures: отсутствующий skill, `trial` вместо `accepted`,
   неверный commit, изменённый practice, unsupported schema.
5. Документировать процедуру обновления pin.

### Критерии готовности

- Каждый перечисленный инвариант имеет positive и negative test.
- Suite проходит на Ubuntu, Windows и macOS либо платформонезависимая часть
  явно запускается на всех поддерживаемых средах.
- Дефект NPR №49 закрыт только после проверки реального BP pin.

## Фаза 5. Завершить version/migration contract NPR

### Действия

1. Сравнить текущий managed `AGENTS.template.md` с опубликованным contract v1.
2. Определить минимальный version bump по правилам проекта.
3. Добавить migration entry для existing projects и проверить состояния:
   `managed_match`, `managed_drift`, `unmanaged_conflict`, malformed и future
   schema.
4. Обновить `STANDARD_VERSION`, metadata expectations, templates, guides,
   fixtures и `CHANGELOG.md` согласованно.
5. Прогнать полный локальный suite из `docs/quality/TESTING.md`.
6. После подтверждения пользователя подготовить release/tag.

### Критерии готовности

- Новый bootstrap записывает актуальную version/provenance metadata.
- Старый проект получает reviewable, fingerprinted migration plan.
- Повторный apply идемпотентен, локальные unmanaged rules сохраняются.
- CI и `macos-smoke` зелёные.
- Дефект NPR №50 перемещён в `Fixed` с release/migration evidence.

## Фаза 6. Наполнить Best Practices

### Scope первой волны

- `common`: минимум ещё две независимо подтверждённые практики;
- `tools`: минимум одна практика с tech-radar verdict;
- `prompts`: минимум одна доказанная prompt/skill practice;
- один реально используемый stack-раздел (`web` или `1c`).

### Действия

1. Выбрать соседние проекты с checked-in `DEFECTS`, `PLAYBOOK`, ADR/research.
2. Создавать по одному candidate на файл и PR.
3. Не повышать evidence выше фактических независимых источников.
4. Review проводить отдельно от harvest; `E1 → trial`, `E2/E3 → accepted`.
5. Для каждого принятого файла проверить provenance, freshness и applicability.

### Критерии готовности

- BP содержит не менее пяти практик минимум в трёх разделах.
- Нет accepted-практик без `E2`/`E3`.
- `make check` и strict freshness проходят на `main`.

## Фаза 7. Consumer pilot и измерение результата

### Действия

1. Выбрать минимум два проекта разных типов.
2. Запустить `apply-best-practices` только после review применимости.
3. Для каждой рассмотренной практики записать outcome:
   `applied`, `already-compliant`, `not-applicable` или `deferred`.
4. Проверить, что `.best-practices.json` содержит source commit и не содержит
   приватных данных.
5. Запустить `practice_metrics.py` по обоим consumers.
6. Записать pilot report: изменения, отклонения, regressions и adoption rate.

### Критерии готовности

- Найдены минимум два consumer manifests.
- Есть минимум одна реально применённая практика.
- Adoption rate вычисляется, а не равен `null`.
- Повторный report не предлагает уже записанное решение как новое.

## Финальный regression gate

### NPR

```sh
for file in scripts/*.sh; do sh -n "$file"; done
sh scripts/test-bootstrap.sh
sh scripts/test-contract.sh
sh scripts/test-agent-setup.sh
sh scripts/test-skills.sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-validator.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-promotion-candidates.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-agent-sync.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-migration-planner.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-standardize-existing-project.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-compress-project.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-supply-chain.py
python3 scripts/check-action-pins.py
python3 scripts/validate-project.py --root . --kind rules --report-only
```

### Best Practices

```sh
make check
```

### GitHub

- оба `main` защищены;
- нет незавершённых PR этой программы;
- последние обязательные runs успешны;
- feature branches не содержат единственную копию production-функционала.

## Итоговый Definition of Done

- Дефекты NPR №48–50 и два открытых дефекта BP переведены в `Fixed` с evidence.
- Оба published `main` содержат согласованные реализации.
- Cross-repo contract удерживается CI, а не только документацией.
- NPR version/migration отражают managed baseline.
- BP содержит полезный минимальный каталог.
- Два consumer projects подтвердили измеримую доставку практик.
