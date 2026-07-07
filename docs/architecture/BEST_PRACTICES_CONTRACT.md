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
skills и hashes, разрешённый status `accepted`, promotion source, retired
routes, active routing surfaces, governance expectation и hash/последствия
ADR-0003.

CI: `python3 scripts/test-best-practices-contract.py`.

Перед promotion:

```sh
python3 scripts/check_best_practices_contract.py \
  --best-practices-root "../Best Practices"
```

Проверка отказывает при другом remote/commit, file hash, practice ID/status,
retired route или изменённом ADR. GitHub governance дополнительно проверяется
в конце структурной фазы через `gh api` согласно [[docs/quality/PLAYBOOK|PLAYBOOK]].

## Обновление pin

1. Обновить BP `main`, выполнить `make check`, проверить protection/PR state.
2. Выбрать accepted practice с достаточной evidence.
3. Обновить commit, hashes, route/ADR expectations отдельным change set.
4. Проверить реальный checkout и полный NPR suite.
5. Не смешивать обновление pin с реализацией правила NPR.

Pin подтверждает целостность источника, но не заменяет решение администратора
об обязательности практики.
