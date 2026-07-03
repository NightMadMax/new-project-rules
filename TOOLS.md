# Tools

## Script entry points

- Полный каталог скриптов `scripts/` с назначением каждого ведётся в
  [[INDEX|INDEX]]; команды и матрица тестов — в
  [[docs/quality/TESTING|TESTING]]. Здесь перечислены только неочевидные
  runtime-требования и ключевые команды.
- Семейства скриптов: `bootstrap-new-project.*` (создание проекта),
  `setup-global-agents.*` и `add-agent-scope.*` (настройка правил),
  `check-environment.*` и `project-doctor.*` (диагностика),
  `validate-project.*`, `sync-global-agents.*`, `plan-migration.*`,
  `standardize-existing-project.*` (контракт и миграции), `test-*` (тесты).
- Каждый инструмент имеет парные `.sh` и `.ps1` entry points для чистых
  машин без Python. Исключение: `test-powershell-environment.ps1` и
  `test-powershell-syntax.ps1` PowerShell-специфичны и sh-пары не имеют.

## Python development dependencies

- Minimum supported runtime for validator and future migrations: Python `3.9`.
- Validator command: `python scripts/validate-project.py --root . --kind rules`.
- Global policy inspection: `python scripts/sync_global_agents.py --check` или
  `python scripts/sync_global_agents.py --diff --report-only`.
- Migration plan: `python scripts/plan_migration.py --plan --target project
  --root <project>` или `--target global`. Apply требует fingerprint из
  проверенного плана и явные `--apply --fingerprint <value> --yes`.
- Existing-project standardization plan:
  `python scripts/standardize_existing_project.py --root <project>`; первая
  версия умеет read-only assessment и безопасный `adopt-in-place` plan/apply
  по fingerprint для отсутствующих managed files и index updates.
- Supply-chain checks: `python scripts/check-action-pins.py` и
  `python scripts/test-supply-chain.py`; external Actions разрешены только по
  full commit SHA, Docker actions — по `sha256` digest.
- Validator runtime uses only the Python standard library.
- Install: `python -m pip install -r requirements-dev.txt`.
- `PyYAML 6.0.3`: required by the official `skill-creator` metadata generator
  and validator used to maintain Agent Skills.
- Verify: `python -c "import yaml; print(yaml.__version__)"`.
- On Windows, set `$env:PYTHONUTF8='1'` for these helpers because their
  `Path.read_text()` calls otherwise use the active legacy code page.

## PowerShell

- Purpose: parse and runtime verification of the portable `.ps1` bootstrap,
  global-agent setup, and scoped-agent setup scripts.
- Installation: `brew install powershell`.
- Installed version: PowerShell `7.6.3`.
- Installed dependency: .NET `10.0.301`.
- Version check: `pwsh --version`.
- Parser check: `pwsh -NoProfile -File scripts/test-powershell-syntax.ps1`.
- Runtime coverage: macOS ARM64 with PowerShell 7.6.3; GitHub Actions additionally
  runs parser and runtime tests with Windows PowerShell 5.1 and PowerShell 7.
- Test commands and the supported environment matrix are maintained in
  [[docs/quality/TESTING|TESTING]].

Project automation should continue to use dependency-free shell and PowerShell
entry points for clean-machine compatibility. Python 3 standard-library code is
preferred when future cross-platform logic becomes complex enough to justify a
shared implementation and Python availability is confirmed on every target.
