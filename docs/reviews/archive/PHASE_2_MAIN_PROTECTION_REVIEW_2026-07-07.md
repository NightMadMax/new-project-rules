---
type: review
status: complete
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/security/THREAT_MODEL]]"
  - "[[docs/quality/DEFECTS]]"
  - "[[ACTIONS]]"
---

# Phase 2 review: защита `new-project-rules/main`

## Scope

Проверены prerequisites и фактическая GitHub-конфигурация защиты default
branch: `.github/CODEOWNERS`, regression test governance surfaces, threat model
и repository ruleset `Protect main` (`id: 18603924`).

## Проверенная конфигурация

- target: `~DEFAULT_BRANCH`;
- enforcement: `active`;
- pull request обязателен;
- один approval и Code Owner review;
- stale reviews сбрасываются после push;
- review threads должны быть разрешены;
- strict required checks: `shell`, `powershell`;
- deletion и non-fast-forward запрещены;
- administrator repository-role bypass сохранён.

`macos-smoke` намеренно не сделан глобальным required context: workflow
path-filtered и не создаёт check для docs-only PR. При изменении `.github`,
`config`, `scripts`, `templates` или `.agents` job `smoke` продолжает
запускаться и должен быть зелёным перед merge.

## Verification

- PR №2 с CODEOWNERS прошёл `shell`, `powershell` и `smoke`;
- supply-chain suite: 8 tests passed;
- action pin check: passed;
- project validator: `0 error(s), 0 warning(s)`;
- GitHub API повторно прочитал ruleset без расхождения;
- branch API вернул `main.protected=true`.

## Code review

Проверен полный diff prerequisites и closeout:

- CODEOWNERS покрывает весь репозиторий и явно перечисляет high-trust surfaces;
- regression test удерживает обязательные governance paths;
- threat model больше не содержит устаревшее утверждение о недоступности
  rulesets;
- required contexts соответствуют реальным job names GitHub Actions;
- path-filtered `smoke` не создаёт deadlock для docs-only PR.

Блокирующих замечаний не найдено.

## Verdict

**Phase 2 approved.** Защита `main` включена и postcondition подтверждён API.
Сознательный administrator bypass остаётся документированной trust boundary.
