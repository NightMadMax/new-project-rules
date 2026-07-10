---
type: research
status: complete
owner: project
last_verified: 2026-07-10
source_of_truth: live consumer checkouts
related:
  - "[[docs/research/CONSUMER_STANDARD_MEASUREMENT]]"
  - "[[docs/reviews/NPR_BP_CLOSEOUT_REVIEW_2026-07-08]]"
---

# Baseline consumer-метрик — 2026-07-10

Проверены `jira-analytics` и `Роутеры и Watchdog`. Для обоих
`validate-project --report-only` вернул 0 errors, 0 warnings, 0 info; profile
`operated`, schema `2`.

| Метрика | Значение | Ограничение |
|---|---:|---|
| Consumers scanned | 2 | оба существующих adopted-проекта |
| Current compliance | 2/2 (100%) | snapshot, не 30/90-day measurement |
| Recorded practice decisions | 6 | source: BP `practice_metrics.py` |
| Practice adoption rate | 4/6 (66.7%) | `applied` + `already-compliant` |
| Time-to-first-green | unknown | первый green output не сохранён |
| Self-service rate | unknown | исторические intervention events не размечены |
| Upgrade lag | unknown | нет новой schema после baseline |

Outcomes: `already-compliant` — 3, `applied` — 1, `not-applicable` — 2.
Best Practices commit: `ff54781f05e9b3f945e75b602aa32cb49ded671e`.

Повторить validator для обоих consumer не позднее 2026-08-09.
