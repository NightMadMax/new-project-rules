---
type: quality-backlog
status: active
owner: project
last_verified: 2026-07-06
source_of_truth: repository
related:
  - "[[docs/quality/PROMOTION_CANDIDATES]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY]]"
---

# Promotion candidate files

Каждый кандидат хранится в отдельном файле
`PC-YYYY-<12-hex>-<slug>.md`. Это устраняет общий mutable hotspot между
независимыми ветками. Legacy ID формата `PC-YYYY-NNN` остаются валидными.

Новые файлы создавайте генератором:

```sh
python3 scripts/promotion_candidates.py create --slug safe-example \
  --title "Safe example" --source "project/artifact" \
  --observation "Observed fact" --generalized-lesson "Reusable lesson" \
  --scope "Applicable projects" --evidence "defect/test/commit" \
  --artifact-type validator --proposed-target "scripts/validate-project.py"
```

Проверка schema и уникальности:

```sh
python3 scripts/promotion_candidates.py validate
```

Не поддерживайте вручную общий список записей: каталог является очередью, а
[[docs/quality/PROMOTION_CANDIDATES]] — стабильной точкой входа и описанием
workflow.

Завершённые `implemented` и `rejected` записи хранятся в
[[docs/quality/promotion-candidates/archive/README|архиве promotion candidates]].
