---
type: code-review
status: complete
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/architecture/BEST_PRACTICES_CONTRACT]]"
  - "[[docs/reviews/A3_SCHEMA2_CONSUMER_WRITER_REVIEW_2026-07-07]]"
  - "[[docs/quality/DEFECTS]]"
---

# Code review A4: cross-repo consumer E2E

## Scope

Проверены CI checkout, pin, real-code import boundary, NPR preference writer,
BP loader/filter/outcome writer и трёхплатформенный запуск.

## Finding

Первый E2E-прогон обнаружил, что A3 принимала синтаксически валидную секцию
`python`, отсутствующую в BP `validate.ALLOWED_STACKS`. Это позволяло NPR
создать manifest, который BP затем отклонял.

## Resolution

- NPR writer использует тот же закрытый набор из семи sections;
- неизвестная, но хорошо сформированная секция блокируется до записи;
- примеры и unit tests используют canonical `web`;
- дефект записан как №54.

## Verification

- pinned checkout проходит hash/HEAD/origin contract check;
- global optout исключает все предложения;
- section optout исключает только соответствующий раздел;
- BP outcome сохраняется после последующего NPR preference update;
- matrix: Ubuntu, Windows, macOS.

## Verdict

A4 принята после исправления найденной enum-несовместимости. Gate проверяет
реальный код обоих репозиториев, а не копию schema fixture.
