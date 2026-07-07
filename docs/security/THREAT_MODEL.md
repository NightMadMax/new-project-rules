---
type: threat-model
status: active
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/architecture/ARCHITECTURE]]"
  - "[[docs/quality/TESTING]]"
  - "[[docs/guides/PLAN_MIGRATIONS]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY]]"
  - "[[ACTIONS]]"
---

# Threat model

## Scope и security goals

Модель покрывает bootstrap, Agent Skills, глобальные инструкции, migration
engine, knowledge promotion, GitHub publication и CI этого репозитория.

Защищаем:

- целостность шаблонов, правил и скриптов, которые наследуют будущие проекты;
- локальные пользовательские дополнения и backup глобальной policy;
- Git/GitHub credentials и отсутствие секретов в Markdown, logs и fixtures;
- воспроизводимость CI на Ubuntu, Windows и macOS;
- reviewability изменений standard schema и migrations.

Не защищаем compromised administrator account, compromised local OS или
злонамеренное изменение после осознанного bypass всех проверок.

## Trust boundaries

```text
GitHub / external Actions
        │ pinned checkout + read-only token
        ▼
Repository contract ──► bootstrap / validator / migrator
        │                         │
        ▼                         ▼
Generated project repo     ~/.codex/AGENTS.md
        │                         │ exact backup
        └────────► Obsidian vault ◄────────┘
```

- GitHub-hosted runners и `actions/checkout` — внешняя supply chain.
- Pull request content недоверенное; workflow token имеет только `contents:
  read`, checkout credentials не сохраняются, secrets не используются.
- `GLOBAL_AGENT_INSTRUCTIONS.md`, templates, skills и migration manifest —
  высокодоверенный executable policy surface.
- Проектные memory и документы недоверенные до review/promotion.
- `~/.codex/AGENTS.md` находится вне Git и изменяется только fingerprint-
  подтверждённой migration с backup.

## Threats и controls

| Threat | Impact | Controls | Residual risk |
|---|---|---|---|
| Mutable Action tag/branch перенаправлен на вредоносный commit | Выполнение чужого кода в CI | Полный SHA, repository `sha_pinning_required`, только GitHub-owned actions, `check-action-pins.py`, regression tests, Dependabot | Review обновлений SHA остаётся обязательным |
| Workflow получает лишние GitHub права | Изменение repository из CI | Repository default `read`, workflow `contents: read`, `persist-credentials: false`, без secrets | GitHub-hosted runner всё ещё обрабатывает содержимое repository |
| `pull_request_target` или untrusted interpolation исполняет PR с secrets | Credential exfiltration | Используется `pull_request`, нет secrets и event-field interpolation | Будущие workflow могут нарушить правило; threat model и review должны обновляться |
| Windows/macOS implementations расходятся | Небезопасный platform-specific output | Ubuntu/Windows CI плюс path-triggered macOS smoke | macOS runner запускается только при значимых путях или вручную |
| Bootstrap/template подменяет инструкции будущих проектов | Массовое распространение вредоносной policy | Contract tests, validator, skill parity, Git history, отдельные migrations, `.github/CODEOWNERS` | Администратор может осознанно применить ruleset bypass |
| Global migration перезаписывает локальный текст или symlink | Потеря правил/ownership | Managed markers, fingerprint, clean source, symlink guard, exact backup, atomic replace, idempotence | Rollback остаётся ручным осознанным действием |
| Project migration пишет поверх пользовательской metadata | Потеря provenance | Existing metadata/symlink блокируют adoption; clean tree; один unstaged JSON; atomic write | Пользователь может закоммитить preview без review |
| Секрет попадает в repository или diagnostic output | Credential compromise | Secret/path validator, redacted structural diff, no credentials in metadata, read-only CI token | Pattern scan не заменяет dedicated secret scanning |
| Локальный project lesson автоматически становится global rule | Policy poisoning | [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Knowledge Promotion]] требует evidence, scope и validation | Ошибка человеческого review остаётся возможной |
| Force-push или deletion переписывает `main` | Потеря audit trail | Git history, GitHub remote, CODEOWNERS и repository ruleset для default branch | Администраторский bypass остаётся сознательной trust boundary |

## Dependency policy

GitHub указывает, что полный commit SHA — единственный immutable способ
подключить action. Поэтому внешние `uses:` принимаются только с lowercase
40-hex SHA; version comment сохраняет читаемость. Docker actions требуют
`sha256` digest, local actions разрешены. См. [GitHub Secure use
reference](https://docs.github.com/en/actions/reference/security/secure-use).

Dependabot еженедельно проверяет ecosystem `github-actions` и создаёт PR для
обновления pin. См. [GitHub Dependabot version
updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configuring-dependabot-version-updates).

Repository Actions policy дополнительно принуждает full SHA и разрешает только
GitHub-owned actions. Настройка и rollback зафиксированы в [[ACTIONS]]; API
поддерживает эти controls согласно [GitHub Actions permissions
reference](https://docs.github.com/en/rest/actions/permissions).

## Verification и response

- Локально: `python scripts/check-action-pins.py` и
  `python scripts/test-supply-chain.py`.
- CI: pin check выполняется до repository scripts; macOS smoke запускается по
  core paths и вручную.
- При подозрительном Action update не обновлять SHA: проверить commit в
  официальном action repository, PR diff и release provenance.
- При утечке credential удалить affected logs/artifacts, отозвать credential,
  проверить Git history и записать incident/defect.
- При ошибочной global migration восстановить exact backup из [[ACTIONS]],
  затем повторить sync check и doctor.

## Governance state

Проверка 2026-07-07 показала, что repository rulesets доступны. До включения
ruleset `main` остаётся незапрещённым для direct push; это записано как дефект
№48. `.github/CODEOWNERS` задаёт владельца всех файлов и отдельно перечисляет
высокодоверенные governance surfaces. После применения ruleset API postcondition
должен подтвердить pull request gate, review, conversation resolution, required
checks, deletion и non-fast-forward protection. Actions SHA/owner policy
остаётся независимым дополнительным control.
