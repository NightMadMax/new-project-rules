---
type: architecture
status: active
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/architecture/decisions/ADR-0002-versioned-project-contract|ADR-0002]]"
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN]]"
  - "[[docs/guides/PLAN_MIGRATIONS]]"
---

# Project standard metadata schema

`.project-standard.json` фиксирует применённую schema, профиль и provenance
стандарта. Это машиночитаемый state migrator, а не описание проекта.

Текущая schema `2`:

```json
{
  "schema_version": 2,
  "profile": "software",
  "source": "NightMadMax/new-project-rules",
  "source_commit": "<40-hex-commit>",
  "created_at": null,
  "adopted_at": "YYYY-MM-DD",
  "applied_migrations": [
    "0001-adopt-project-standard",
    "0004-upgrade-project-standard-v2"
  ]
}
```

## Инварианты

- `schema_version` — положительное целое, не release version.
- `profile` — `minimal`, `software`, `operated` или `all`.
- `source` берётся из `config/standard-source.txt`, а `source_commit` — из
  проверенного commit репозитория правил; локальный путь и remote с credentials
  не записываются.
- Для нового проекта `created_at` содержит дату bootstrap. При adoption legacy
  проекта она равна `null`, потому что migrator не выдумывает историческую дату.
- `adopted_at` фиксирует дату adoption, а `applied_migrations` — уникальные ID
  уже применённых преобразований.
- Metadata не содержит токены, имя компьютера или абсолютные пути.

Migration manifest `config/migrations.tsv` является источником истины для ID,
target, перехода schema и handler. Legacy state обозначается schema `0`.
Planner строит единственную последовательную цепочку до текущей schema;
пропущенный или неоднозначный переход блокирует запись.
