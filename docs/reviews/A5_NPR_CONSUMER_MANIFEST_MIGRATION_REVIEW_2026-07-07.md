---
type: code-review
status: complete
owner: project
last_verified: 2026-07-07
source_of_truth: .best-practices.json
related:
  - "[[docs/architecture/BEST_PRACTICES_CONTRACT]]"
  - "[[docs/reviews/A4_CROSS_REPO_CONSUMER_E2E_REVIEW_2026-07-07]]"
---

# Review A5: NPR consumer manifest migration

## Reviewed plan

- preimage SHA-256: `17d7d1b5512c4caad46af79050727408665bec9a35ddf45912daf0c73c815385`;
- fingerprint: `d08d2ae1945088b8ff92653746e80760b33f3dd5e42788287767d0376d649c20`;
- transition: schema 1 → 2.

## Diff review

Изменены только `schema_version` и новый блок `preferences` со значениями
`global=ask`, `sections={}`. Все три practice ID, outcome, path, source commit,
date и notes сохранены без изменений.

## Verification

- apply повторно проверил clean tree, fingerprint и preimage;
- canonical BP loader принимает результат как schema 2;
- NPR unit и cross-repo E2E suites проходят;
- изменение оставлено unstaged до review.

## Verdict

Миграция NPR принята. Изменение семантически нейтрально для записанных outcomes.
