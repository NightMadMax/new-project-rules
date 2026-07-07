---
type: testing
status: active
owner: project
last_verified: 2026-07-03
source_of_truth: repository
related:
  - "[[INDEX]]"
  - "[[docs/reviews/CODE_REVIEW_scripts_2026-06-28]]"
---

# Проверка скриптов

## Поддерживаемые среды

| Среда | Проверка |
|---|---|
| macOS, системный `sh` | Локальная обязательная проверка перед публикацией и workflow `macos-smoke` |
| Ubuntu, `sh` | GitHub Actions (`ci`) |
| Windows PowerShell 5.1 | GitHub Actions (`ci`) |
| PowerShell 7 | Локально и в GitHub Actions (`ci`, Windows) |
| Python 3.9+ stdlib | Python regression suites (включая standardization) на Ubuntu, Windows и macOS |

Workflow `macos-smoke` запускается на push/PR, затрагивающих workflows,
`config/`, `scripts/`, `templates/` или `.agents/`, и дублирует shell- и
Python-suites на macOS runner. Локальный прогон на macOS остаётся обязательным
перед публикацией.

## Локальные команды

```sh
for file in scripts/*.sh; do sh -n "$file"; done
sh scripts/test-bootstrap.sh
sh scripts/test-contract.sh
sh scripts/test-agent-setup.sh
sh scripts/test-skills.sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-validator.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-promotion-candidates.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-agent-sync.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-migration-planner.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-standardize-existing-project.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-compress-project.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-supply-chain.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-best-practices-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test-best-practices-manifest.py
python3 scripts/check-action-pins.py
python3 scripts/validate-project.py --root . --kind rules --report-only
python3 scripts/sync_global_agents.py --check --report-only
python3 scripts/plan_migration.py --plan --target global --report-only
python3 scripts/standardize_existing_project.py --root . --json
```

```powershell
.\scripts\test-powershell-syntax.ps1
.\scripts\test-powershell-environment.ps1
.\scripts\test-bootstrap.ps1
.\scripts\test-contract.ps1
.\scripts\test-agent-setup.ps1
.\scripts\test-skills.ps1
$env:PYTHONDONTWRITEBYTECODE = "1"
python .\scripts\test-validator.py
python .\scripts\test-promotion-candidates.py
python .\scripts\test-agent-sync.py
python .\scripts\test-migration-planner.py
python .\scripts\test-standardize-existing-project.py
python .\scripts\test-compress-project.py
python .\scripts\test-supply-chain.py
python .\scripts\test-best-practices-contract.py
python .\scripts\test-best-practices-manifest.py
python .\scripts\check-action-pins.py
python .\scripts\validate-project.py --root . --kind rules --report-only
python .\scripts\sync_global_agents.py --check --report-only
python .\scripts\plan_migration.py --plan --target global --report-only
python .\scripts\standardize_existing_project.py --root . --json
```

PowerShell-проверки следует выполнять в Windows PowerShell 5.1 и PowerShell 7.
Parser-check обязан возвращать ненулевой код, если хотя бы один файл содержит
синтаксическую ошибку.

## Проверяемые сценарии

- создание всех bootstrap-профилей и точный состав файлов;
- валидная `.project-standard.json` provenance metadata для каждого нового
  профиля и явный отказ bootstrap без Git;
- parity фактических shell/PowerShell outputs с `config/profiles.tsv`;
- доказательство manifest-driven поведения через изменённую изолированную копию
  contract без правок bootstrap adapters;
- валидность `STANDARD_VERSION` и обязательных policy literals;
- полнота `docs/README.md` для расширенных профилей;
- валидность Agent Skills, совпадение Claude-мостов и канонических metadata;
- наличие обязательных Knowledge Promotion и Defect Tracking в переносимых
  global/project rules;
- начальный commit при настроенной Git-идентичности;
- staged-состояние без commit при отсутствующей идентичности;
- корректный отказ при ошибке `git init`, `git add`, `git status` или commit;
- rollback отсутствующего или изначально пустого destination при ошибке;
- shell-запуск напрямую, через `PATH` и символическую ссылку;
- создание, повторный запуск и конфликт global/scoped agent setup;
- отказ от scope path traversal до создания каталога;
- режимы environment check `codex`, `claude` и `both`;
- validator profile inference, explicit profile, metadata readiness и отсутствие
  mutation;
- validator findings для missing artifacts, wikilinks, placeholders, nested
  vault, raw memory, secrets и machine-specific paths;
- стабильные validator exit codes `0` / `1` / `2` и `report-only`;
- doctor fallback без Python, Git/Obsidian diagnostics и secret-safe global
  policy drift detection;
- global sync states `missing`, `legacy_exact`, `unmanaged_conflict`,
  `managed_match`, `managed_drift`, `malformed` и `unsupported_schema`;
- secret-safe hash/range diff, сохранение текста вне managed block и отсутствие
  mutation во всех read-only режимах;
- migration manifest uniqueness/schema transitions, exact profile inference,
  clean-tree blockers и строгая `.project-standard.json` schema;
- reviewable metadata preview, secret-safe global adoption plan, стабильные
  planner exit codes и доказательство отсутствия mutation;
- decision report для legacy-проекта, рекомендации `adopt-in-place` /
  `re-bootstrap-from-existing`, conflict detection для `CLAUDE.md` и nested
  `.obsidian`, а также отсутствие mutation у standardization planner;
- распознавание `rules-repository`, отчёт `not_applicable`, отсутствие profile
  inference и блокировка всех consumer plan/apply до mutation; одиночный
  `STANDARD_VERSION` в consumer project не считается rules repository;
- fingerprinted `adopt-in-place` apply только для safe files, rejection при
  mismatch fingerprint и обновление index links без перезаписи сложных docs;
- `re-bootstrap-from-existing` plan/apply, bootstrap нового проекта, перенос
  только safe transfer set и сохранение bootstrap docs без перезаписи legacy
  документации;
- fingerprint mismatch/stale preimage rejection, обязательный confirmation,
  atomic-write cleanup при interruption и повторная pre-apply validation;
- project apply как единственный unstaged metadata file, точный global backup,
  managed-match postcondition и идемпотентный повторный apply;
- отказ global migration заменять existing symlink обычным файлом;
- восстановление HOME/Git process environment после PowerShell bootstrap и
  contract suites, включая отсутствие пустых identity variables;
- full 40-hex pins для external Actions, `sha256` для Docker actions, разрешение
  local actions и отказ от mutable tags/branches;
- pinned compatibility contract Best Practices: schema, repository identity,
  required skills, accepted promotion source, commit и file hashes;
- schema 2 consumer writer: global/section preferences, сохранение outcomes,
  отказ от неявной schema 1 migration и symlink safety;
- path-triggered/manual macOS smoke для shell, bootstrap, contract, skills и
  Python policy suites;
- точные импорты `CLAUDE.md` и отсутствие дублей в `INDEX.md`;
- UTF-8 без BOM, отсутствие шаблонных плейсхолдеров и чистое git-дерево.
