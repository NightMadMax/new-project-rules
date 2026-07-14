---
type: architecture
status: active
owner: project
last_verified: 2026-07-07
source_of_truth: config/best-practices-contract.json
related:
  - "[[docs/architecture/ARCHITECTURE]]"
  - "[[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY]]"
---

# Compatibility contract NPR ↔ Best Practices

`config/best-practices-contract.json` закрепляет совместимую версию BP без
сетевой зависимости CI. Он хранит repository identity, commit SHA, обязательные
skills, consumer manifest interface и hashes, разрешённый status `accepted`,
promotion source, retired routes, active routing surfaces, governance
expectation и hash/последствия ADR-0003.

CI: `python3 scripts/test-best-practices-contract.py`.

CI дополнительно checkout'ит `source_commit` в изолированный каталог и запускает
`scripts/test-best-practices-e2e.py`: NPR writer создаёт preferences, а реальный
BP `practice_report.py` загружает их, применяет optout и записывает outcome.
До reader/writer assertions gate запускает полную repository validation и
реальный schema-2 report. Gate выполняется на Ubuntu, Windows и macOS.

Перед promotion:

```sh
python3 scripts/check_best_practices_contract.py \
  --best-practices-root "../Best Practices"
```

Проверка отказывает при другом remote/commit, file hash, practice ID/status,
retired route или изменённом ADR. GitHub governance дополнительно проверяется
в конце структурной фазы через `gh api` согласно [[docs/quality/PLAYBOOK|PLAYBOOK]].

Scheduled workflow `bp-pin-watch` сравнивает reviewed pin с текущим BP `main`,
checkout'ит live `main`, выполняет repository validation и representative report.
Drift или невалидная база создаёт красный read-only signal, но не обновляет
commit, hashes или consumer outcomes.

## Compatibility и deprecation

- Неизвестная schema compatibility manifest — hard failure.
- Изменение любого hashed interface-файла считается несовместимым до отдельного
  NPR PR с review diff, новыми hashes и green cross-repo E2E.
- Consumer manifest schema 2 — canonical write format. Schema 1 поддерживается
  только read-only normalization/migration; новые schema-1 файлы запрещены.
- Удалять backward reader можно только после миграции известных consumers,
  отдельного major contract decision и документированного периода deprecation.
- Новый BP `main` не означает автоматическую доставку практик: status, evidence
  и applicability по-прежнему проходят review.

## Обновление pin

1. Обновить BP `main`, выполнить `make check`, проверить protection/PR state.
2. Выбрать accepted practice с достаточной evidence.
3. Обновить commit, hashes, route/ADR expectations отдельным change set.
4. Проверить реальный checkout и полный NPR suite.
5. Не смешивать обновление pin с реализацией правила NPR.

Проверка drift вручную:

```sh
python3 scripts/check_best_practices_contract.py --check-latest
```

Pin подтверждает целостность источника, но не заменяет решение администратора
об обязательности практики.
