---
type: research
status: active
owner: project
last_verified: 2026-07-10
source_of_truth: consumer evidence and Best Practices reports
related:
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN]]"
  - "[[docs/research/CONSUMER_STANDARD_BASELINE_2026-07-10]]"
  - "[[docs/architecture/BEST_PRACTICES_CONTRACT]]"
---

# Измерение результата стандарта на consumer-проектах

Это продуктовая программа, а не новый compatibility contract. Outcomes практик
остаются в `.best-practices.json`: их записывает `practice_report.py`, а
`practice_metrics.py` агрегирует.

| Метрика | Определение | Доказательство |
|---|---|---|
| Time-to-first-green | время от `created_at` до первого green validator | timestamp создания + сохранённый validator/CI output |
| Self-service rate | доля запусков без ручного вмешательства в стандарт | запись с `self_service` и причиной |
| Compliance 30/90 | green validator на 30-й/90-й день | повторный validator в соответствующую дату |
| Upgrade lag | время от новой schema до миграции consumer | дата release + `applied_migrations` |
| Manual interventions | число и причина ручных изменений стандарта | `ACTIONS.md` или review с явной меткой |

Не выводить отсутствующие исторические значения из git-дат или текста журналов:
они остаются `unknown`.

## Операционный цикл

1. При создании consumer сохранить время создания и первый green output.
2. При помощи/исправлении стандарта записать intervention и причину в `ACTIONS.md`.
3. На 30-й и 90-й день выполнить `validate-project --report-only`.
4. После изменения schema записать дату доступности и успешной миграции.
5. Раз в цикл агрегировать practice outcomes:

```sh
python3 "../Best Practices/scripts/practice_metrics.py" --root "../Best Practices" \
  --consumer "<consumer-1>" --consumer "<consumer-2>"
```

`jira-analytics` и `Роутеры и Watchdog` — baseline cohort. Они adopted, а не
созданы bootstrap, поэтому их исторические time-to-first-green и self-service
неизвестны; измеряются текущий compliance и будущий upgrade lag.
