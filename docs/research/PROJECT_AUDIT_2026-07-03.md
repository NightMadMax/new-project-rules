---
type: research
status: active
owner: project
last_verified: 2026-07-03
source_of_truth: repository
related:
  - "[[docs/research/PROJECT_AUDIT_2026-07]]"
  - "[[docs/quality/DEFECTS]]"
  - "[[docs/quality/TESTING]]"
  - "[[docs/security/THREAT_MODEL]]"
---

# Повторный глубокий аудит проекта — 2026-07-03

## Цель и метод

Аудит выполнен с нуля после крупных изменений. Проверены repository contract,
правила и их суммарный бюджет, bootstrap, validator, global-policy sync,
migration engine, standardization workflow, skills и Claude bridges, CI,
GitHub Actions policy, документация и внешние ссылки.

Метод включал:

- полный локальный POSIX/Python regression suite;
- PowerShell 7 прогон на macOS;
- изолированные adversarial fixtures для symlink, stale fingerprint и
  destination containment;
- live GitHub API проверку Actions permissions, runs и branch protection;
- сверку Codex с актуальным official manual и Claude Code/GitHub с официальной
  документацией;
- HTTP-проверку всех 50 внешних URL в Markdown.

## Итог

Проект имеет сильный и проверяемый фундамент, но использовать apply-режимы
`standardize-existing-project` пока небезопасно. Read-only assessment,
bootstrap, validator, global migration planner и supply-chain controls выглядят
зрелыми. Новый destructive standardization workflow добавлен быстрее, чем его
security boundaries и CI coverage.

Оценка состояния:

| Область | Статус | Вывод |
|---|---|---|
| Contract и bootstrap | Green | Manifest-driven parity и rollback покрыты |
| Validator и metadata migrations | Green | Негативные сценарии и atomic global/project metadata apply покрыты |
| GitHub/CI supply chain | Green | SHA pinning и GitHub-owned Actions принудительно включены |
| Agent rules и skills | Green/Amber | Согласованы, но instruction budget 299/300 без запаса |
| Cross-platform diagnostics | Amber | Два локальных PowerShell/macOS сбоя и SSH false positive |
| Existing-project standardization apply | Red | Подтверждены записи/копирование вне границ и stale review |

## Что сделано хорошо

1. `STANDARD_VERSION` и TSV manifests отделяют контракт от platform adapters.
2. Bootstrap parity доказана изменяемой изолированной копией manifest, а не
   только сравнением двух реализаций.
3. Global policy migration использует managed markers, fingerprint, backup,
   atomic replace, symlink guard и secret-safe diagnostics.
4. Validator проверяет профили, metadata schema, wikilinks, frontmatter,
   nested vault, raw memory, секреты и machine-specific paths.
5. External Actions pinned по full SHA; live GitHub API подтвердил
   `allowed_actions=selected`, `github_owned_allowed=true` и
   `sha_pinning_required=true`.
6. Codex/Claude portability реализована через канонические `.agents/skills/` и
   минимальные `.claude/skills/` bridges; 8/8 проходят contract tests.
7. Документационная навигация связна; validator не нашёл broken wikilinks.
8. Все 50 внешних Markdown URL вернули HTTP 200 на момент проверки.

## Подтверждённые дефекты

### P0 — standardization apply временно не использовать

#### DEFECT 35: запись через symlink за пределы проекта

Tracked `INDEX.md`, указывающий symlink на внешний файл, был принят как
`status=ready`. Apply прошёл с корректным fingerprint и изменил внешний target.
Post-validator вернул 0 errors. Причина: planned destinations не проверяются
через `is_symlink()` и containment перед `write_text()`.

#### DEFECT 36: копирование внешнего содержимого через source symlink

`src/linked-secret.txt` был symlink на внешний файл. Re-bootstrap разыменовал
его через `shutil.copy2()` и записал внешнее содержимое в новый repository как
обычный файл. Это может перенести credentials или machine-local data.

#### DEFECT 37: fingerprint не защищает содержимое transfer set

После review плана содержимое `src/app.txt` было изменено. Тот же fingerprint
успешно прошёл apply, и новое непроверенное содержимое было перенесено.
Fingerprint включает только top-level path names, а не immutable file manifest
с типами, размерами и SHA-256.

#### DEFECT 40: destination может находиться внутри source и `.git`

Планы для `legacy/src/new-project` и `legacy/.git/nested-project` вернули
`status=ready`. Guard проверяет равенство source/destination, но не запрещает
destination быть потомком legacy root.

До исправления этих четырёх дефектов допустимы только read-only assessment и
plan для анализа. `--apply` для `adopt-in-place` и
`re-bootstrap-from-existing` считать заблокированным.

### P1 — coverage и cross-platform

#### DEFECT 34: standardization suite отсутствует в CI

`scripts/test-standardize-existing-project.py` проходит локально, но не
запускается ни в Ubuntu/Windows job, ни в macOS smoke. Поэтому зелёный CI не
покрывает destructive workflow, в котором обнаружены P0 дефекты.

#### DEFECT 38: PowerShell scope setup падает на macOS

`/var/...` и `/private/var/...` сравниваются как разные roots, хотя это один
файловый объект. Валидный nested scope ошибочно отклоняется.

#### DEFECT 39: credential helper false positive при SSH transport

При `gh git_protocol=ssh` и `origin=git@github.com:...` environment check всё
равно требует HTTPS `credential.helper`, возвращает exit 1 и предлагает
ненужную настройку. Проверка должна учитывать transport и фактическую Git auth.

### Известный ранее

- DEFECT 33: `test-bootstrap.ps1` на macOS сохраняет stale command resolution
  удалённого mock `git`; повторно воспроизведён.

Все записи находятся в [[docs/quality/DEFECTS]].

## Результаты проверок

- Shell bootstrap: 122/122.
- Shell contract: 70/70.
- Agent setup: 47/47.
- Skills: pass.
- Python suites: validator 14, agent sync 7, migration planner 14,
  standardization 8, supply chain 7 — все pass.
- Repository validator: 0 errors / 0 warnings до добавления audit artifacts.
- Global policy: `managed_match`; global migration: `up_to_date`.
- PowerShell syntax: 15 files pass; PowerShell contract: 71 checks pass.
- GitHub post-merge `ci` и `macos-smoke`: success.

Зелёные базовые тесты не опровергают P0: adversarial symlink/content fixtures
отсутствуют в regression suite, а сам standardization suite отсутствует в CI.

## Внешняя сверка

Основные текущие решения подтверждены официальными источниками:

- Codex загружает repo skills из `.agents/skills`, поддерживает project
  `.codex/config.toml`, hooks и combined `project_doc_max_bytes`; custom prompts
  deprecated: [Codex manual](https://developers.openai.com/codex/codex-manual.md).
- Claude Code различает `CLAUDE.md`, skills, settings и hooks; security boundary
  лучше задавать permissions/hooks, а не только текстовой инструкцией:
  [Claude directory](https://code.claude.com/docs/en/claude-directory),
  [hooks](https://code.claude.com/docs/en/hooks),
  [memory](https://code.claude.com/docs/en/memory).
- Full commit SHA остаётся рекомендуемым immutable pin для Actions:
  [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use).

## Приоритет исправлений

1. Заблокировать standardization apply при любом symlink в planned
   source/destination и при выходе resolved path за ожидаемый root.
2. Запретить re-bootstrap destination внутри legacy root, включая `.git`.
3. Строить deterministic recursive transfer manifest: relative path, file type,
   size и SHA-256; включать manifest в fingerprint и повторно проверять перед
   первой записью.
4. Сделать apply transactional: staging directory/atomic promotion для нового
   проекта и cleanup/rollback при ошибке.
5. Добавить adversarial regression tests и включить standardization suite во все
   релевантные CI jobs.
6. После кода обновить [[docs/security/THREAT_MODEL]]: existing-project source,
   transfer set и destination являются отдельными trust boundaries.
7. Исправить canonical path comparison в PowerShell и transport-aware credential
   diagnostics.
8. Снизить instruction chain с 299 хотя бы до 260–280 непустых строк, чтобы
   будущая обязательная правка не нарушала бюджет.

## Решение о готовности

Проект готов как генератор новых проектов и read-only диагностический стандарт.
Он не готов как безопасный автоматический migrator произвольных legacy trees.
Следующий цикл должен быть не расширением функциональности, а hardening
standardization engine и его CI gate.
