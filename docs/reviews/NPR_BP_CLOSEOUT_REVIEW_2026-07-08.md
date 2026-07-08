---
type: review
status: complete
owner: project
last_verified: 2026-07-08
source_of_truth: repository-and-github
related:
  - "[[docs/research/NPR_BP_REMEDIATION_PLAN_2026-07-07]]"
  - "[[docs/architecture/BEST_PRACTICES_CONTRACT]]"
  - "[[docs/quality/DEFECTS]]"
---

# Финальный live-аудит NPR ↔ Best Practices

## Scope и вывод

Проверены опубликованные `main`, GitHub governance, pinned contract, CI,
scheduled drift detection и два consumer-проекта. Программа исправлений NPR ↔
Best Practices завершена. Новые практики в этом closeout не собирались и не
применялись.

Дефект №59 исключён из scope по решению пользователя и остаётся в секции
`Open`; это единственный известный открытый дефект NPR на момент проверки.

## NPR

- `main` синхронизирован с `origin/main`, рабочее дерево было чистым до
  подготовки этого отчёта.
- Открытых PR нет; последние `ci`, `macos-smoke` и `bp-pin-watch` успешны.
- `scripts/check_best_practices_contract.py --check-latest` проходит.
- `scripts/validate-project.py` возвращает 0 errors, 0 warnings, 0 info.
- Active ruleset `Protect main` (`18603924`) требует PR, один approval, Code
  Owner review, resolved threads, strict checks `shell`, `powershell` и три
  `cross-repo-e2e` context для Ubuntu, Windows и macOS; deletion и
  non-fast-forward запрещены.
- Branch API возвращает `main.protected=true`.

## Best Practices

- `main` синхронизирован с `origin/main`; открытых PR нет.
- Последний workflow `Validate` успешен.
- `make check`: 63 unit tests, validator и strict freshness прошли.
- Active ruleset `Protect main` (`18538769`); branch API возвращает
  `main.protected=true`.
- NPR pin указывает на BP commit
  `07583c90d7def43fc3709114e2442625d1be6d8e`.

## Consumers и метрики

Проверены `jira-analytics` и `router-watchdog-ops`:

- локальные `main` совпадают с `origin/main`, рабочие деревья чистые;
- открытых PR нет;
- NPR validator для профиля `operated`: 0 errors, 0 warnings в обоих проектах;
- managed global policy совпадает с portable source;
- оба `.best-practices.json` имеют schema `2` и `global: ask`;
- записано шесть решений: `already-compliant` — 3, `applied` — 1,
  `not-applicable` — 2;
- adoption rate: 4/6 = 66,7%;
- повторный applicability report корректно показывает три ранее рассмотренные
  accepted-практики для каждого consumer.

У consumer-репозиториев нет GitHub Actions runs и branch protection. Для
текущего single-maintainer operated-профиля это не является нарушением
контракта NPR и не блокирует closeout; при появлении команды или production
release-процесса governance следует усилить отдельно.

## Итог

Фазы 0–7 и C4 имеют проверяемые postconditions. Связка удерживается executable
contract, трёхплатформенным E2E и scheduled pin-watch. Следующий этап должен
быть отдельной продуктовой программой измерения стандарта на новых проектах, а
не продолжением remediation backlog.
