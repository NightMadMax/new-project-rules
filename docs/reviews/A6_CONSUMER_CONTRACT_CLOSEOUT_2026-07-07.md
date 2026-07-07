---
type: code-review
status: complete
owner: project
last_verified: 2026-07-07
source_of_truth: config/best-practices-contract.json
related:
  - "[[docs/architecture/BEST_PRACTICES_CONTRACT]]"
  - "[[docs/reviews/A4_CROSS_REPO_CONSUMER_E2E_REVIEW_2026-07-07]]"
  - "[[docs/reviews/A5_NPR_CONSUMER_MANIFEST_MIGRATION_REVIEW_2026-07-07]]"
---

# A6: consumer contract closeout

## Integrated state

- BP pin: `e255b6474002ec3a5c4ff16935a24229e9ebf614`;
- NPR и BP consumer manifests используют schema 2;
- migration engine включён в обязательный hashed consumer interface;
- workflow checkout и machine-readable contract используют один commit;
- NPR writer и BP loader/report проверяются real-code E2E на трёх ОС.

## Phase commits and reviews

| Step | Published evidence |
|---|---|
| A2 migration engine | BP PR №19, merge `c837040` |
| A3 schema 2 writer | NPR PR №15, merge `5e97b56` |
| A4 cross-repo E2E | NPR PR №16, merge `c49a0c8` |
| A5 NPR migration | NPR PR №17, merge `a916bc5` |
| A5 BP migration | BP PR №20, merge `e255b64` |

## Final review

Проверены pin/required hashes, workflow ref, schema 2 manifests, сохранённые
outcomes, закрытые defects и серверное состояние GitHub. Контракт отказывает
при missing migration engine, другом checkout HEAD, hash drift или расхождении
workflow pin.

## Verification gate

- live `check_best_practices_contract.py` против BP `main`;
- NPR unit, contract, supply-chain, validator и cross-repo E2E suites;
- BP `make check` и strict freshness;
- GitHub CI обоих репозиториев;
- отсутствие открытых PR после merge A6 и успешные последние `main` runs.

## Verdict

Фаза A закрыта после merge текущего pin change и повторной live-проверки
серверного состояния.
