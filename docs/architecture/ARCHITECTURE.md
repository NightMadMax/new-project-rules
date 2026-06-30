---
type: architecture
status: active
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[PROJECT]]"
  - "[[INDEX]]"
  - "[[docs/architecture/decisions/ADR-0001-two-level-documentation|ADR-0001]]"
  - "[[docs/research/PROJECT_ARTIFACT_MODEL|PROJECT_ARTIFACT_MODEL]]"
---

# Архитектура

Проект состоит из шести слоёв:

1. `STANDARD_VERSION` и `config/` задают версию и машиночитаемый контракт
   профилей, policy blocks и index relationships.
2. [[GLOBAL_AGENT_INSTRUCTIONS]] задаёт поведение агента до открытия проекта.
3. [[AGENTS]] задаёт локальные правила конкретного репозитория.
4. [[TEMPLATES]] описывает переиспользуемые артефакты.
5. `scripts/` создаёт новый проект/repo внутри общего vault из выбранного
   профиля.
6. `.agents/skills/` хранит канонические Agent Skills для Codex, а
   `.claude/skills/` — минимальные мосты Claude Code к тем же workflow.

Родительская рабочая папка является Obsidian vault. Каждый вложенный проект —
отдельный git-репозиторий без собственной `.obsidian`. Один набор Markdown-
файлов используется Obsidian и агентами (Codex, Claude Code) без копирования.

Машиночитаемые источники истины не преобразуются в ручные Markdown-копии.

Скиллы используют общий стандарт `SKILL.md`. Инструкции не копируются между
агентами: Claude-мост указывает на канонический skill в `.agents/skills/`.
Документация хранит назначение, связи, ограничения и эксплуатационный контекст.

Оба bootstrap-адаптера читают `config/profiles.tsv` напрямую. Manifest задаёт
минимальный профиль, источник, destination и связи с обоими индексами;
platform-specific код отвечает только за запись generated artifacts, template
substitution, Git и безопасный rollback. Parity-тесты согласно
[[docs/architecture/decisions/ADR-0002-versioned-project-contract|ADR-0002]]
проверяют contract на обеих платформах и доказывают manifest-driven поведение в
изолированной копии.

`scripts/validate-project.py` является общей read-only validation logic на
Python 3.9 standard library. Native wrappers проверяют runtime и сохраняют
единые exit codes. Project doctor сначала выполняет platform environment check,
затем validator с дополнительной диагностикой Git, global agent policy и
родительского Obsidian vault. Auto-fix отсутствует: диагностика не владеет
пользовательскими файлами.

`scripts/sync_global_agents.py` отделяет portable policy от локальных
дополнений managed markers с `schema=1`. Read-only `check` и secret-safe `diff`
различают missing, legacy, conflict, match, drift и повреждённую grammar;
содержимое active file в отчёт не попадает. Текст вне managed block сохраняется
как пользовательский. Запись, backup и marker migration намеренно отложены до
отдельного подтверждаемого migration workflow.

`config/migrations.tsv` задаёт переходы schema и handlers. Общий
`scripts/project_metadata.py` реализует [[docs/architecture/PROJECT_STANDARD_SCHEMA|metadata schema]],
которую используют validator и `scripts/plan_migration.py`. Planner проверяет
точный профиль, clean Git trees и committed provenance, затем показывает
reviewable project JSON или secret-safe global structural plan. Текущая граница
apply требует точный fingerprint просмотренного плана и явный confirmation.
Перед записью planner повторяет preconditions: project target получает один
atomic-written unstaged metadata file, а global target — побайтовый timestamped
backup и atomic replace с сохранением внешнего пользовательского текста.

CI является отдельной trust boundary. Все external Actions pinned по full
commit SHA, checkout не сохраняет credentials, workflow token read-only, а
`scripts/check-action-pins.py` проверяет policy до основных тестов. Dependabot
предлагает обновления SHA через PR. Ubuntu/Windows дают основной regression
gate; macOS smoke запускается вручную и при изменениях core paths. Угрозы и
residual risks описаны в [[docs/security/THREAT_MODEL]].
