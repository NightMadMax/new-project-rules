---
type: guide
status: active
owner: project
last_verified: 2026-07-14
source_of_truth: repository-and-github-api
related:
  - "[[docs/security/THREAT_MODEL]]"
  - "[[docs/quality/TESTING]]"
  - "[[ACTIONS]]"
---

# Правила работы с GitHub

## Доступ и публикация

- Владелец `NightMadMax` может делать прямой push в `main` через осознанный
  Admin-bypass, но обязан до push прогнать профильные проверки и после push
  дождаться зелёных required checks.
- Владелец должен оставаться единственным Admin. Другим разработчикам выдавать
  максимум Write/Maintain; их изменения проходят через Pull Request и ruleset.
- Перед созданием PR, release, issue, изменением remote/ruleset или destructive
  history operation нужно отдельное подтверждение пользователя. Обычный
  согласованный push текущих изменений выполняется по repository workflow.
- Изменения GitHub governance фиксировать в [[ACTIONS]] с API-postcondition и
  rollback; обычные code/docs changes остаются в Git history.

## Rulesets и CI

- Не менять required-check context случайно. При переводе job в matrix вынести
  matrix в отдельный job, а прежнее имя required check сохранить агрегирующим
  job, который падает при неуспехе любой платформы.
- После изменения workflows проверить immutable Action pins, permissions,
  точные имена required checks и запустить workflow через `workflow_dispatch`,
  если он scheduled-only.
- Прямой push владельца не доказывает качество: завершение работы требует
  зелёного remote CI. Проверять через `gh run list`, `gh run view` или
  `gh run watch`.

## GitHub API и токены

- Полный governance-аудит запускать под пользовательской авторизацией:
  `python scripts/check_github_governance.py`. Он проверяет оба ruleset, точный
  `RepositoryRole id=5` и единственного owner-admin.
- Не использовать стандартный `GITHUB_TOKEN` для cross-repository governance:
  он repository-scoped, не читает collaborators соседнего repo и может скрывать
  actor ID. Scheduled workflow выполняет только self-audit собственного
  репозитория с `--github-token-scope`; ограничение должно быть явным.
- Не создавать PAT, GitHub App, deploy key или repository secret без отдельного
  согласования. Никогда не записывать credential в репозиторий или логи.

## Минимальная проверка

```powershell
python scripts/check_github_governance.py
gh run list --limit 10
git status --short --branch
```

Для Best Practices стабильный required check называется `validate`; для NPR —
`shell`, `powershell` и три `cross-repo-e2e` context.
