# Журнал изменений

Старые релизы перенесены в [[CHANGELOG_ARCHIVE|архив журнала изменений]].

## Unreleased

### Добавлено

- В [[docs/quality/DEFECTS|журнале дефектов]] зафиксированы два сбоя реального
  создания проекта: validation `practice_report.py` на актуальной базе Best
  Practices и невозможность запуска packaged `codex.exe` из PowerShell для
  проверки instruction sources.

- Bootstrap создаёт machine-readable журнал `STANDARD_ADOPTION.json`; новый
  `standard-metrics.py` записывает первый green/self-service и ручные
  вмешательства, затем сводит их read-only отчётом.

- Протокол consumer-метрик и baseline двух operated-проектов: текущий compliance
  2/2 и шесть recorded practice decisions; исторически неизвестные показатели
  явно не подменяются косвенными оценками.

- Единое [[docs/guides/user-guide/USER_GUIDE|пользовательское руководство]] по
  установке, Obsidian vault, безопасным запросам агенту и основным workflow;
  альтернативный черновик устранён, навигация обновлена.
- Папка [[docs/guides/user-guide/README|user-guide]] с основным руководством и
  каталогом визуальных workflow по процессам (полный процесс + workflow
  пользователя + workflow администратора); первый образец —
  Best Practices ↔ new-project-rules.
- [[docs/guides/user-guide/workflows/best-practices-admin|Workflow администратора]]
  как парный ролевой отчёт: разбор кандидатов, затвердевание практики в правило,
  поддержание pin.
- Skill [[.agents/skills/document-process-workflow/SKILL|document-process-workflow]]:
  создание и поддержание в актуальности workflow-отчётов процессов (модель полей,
  схема наименования, два маршрута 🗣/⌨, Markdown+HTML, синхронизация индексов).
- Отчёты [[docs/guides/user-guide/workflows/setup-new-computer-user|«Настройка нового компьютера»]]
  и [[docs/guides/user-guide/workflows/projects-user|«Работа с проектами»]]
  (workflow пользователя): у шагов два маршрута — фраза агенту и скрипт вручную.
- Выбор стека при создании проекта: `create-new-project` спрашивает стек(и)
  (можно несколько или пропустить), `best_practices_manifest.py` получил флаг
  `--stack` и записывает выбор в `.best-practices.json`, применяются практики
  выбранных стеков плюс `common`. Обновлены гайд `CREATE_NEW_PROJECT` и отчёт
  `projects-user`.

### Изменено

- Расширен список стеков Best Practices: добавлены `backend`, `mobile`,
  `desktop`, `data-ml`, `data-analysis`, `excel-research`, `powerbi`,
  `jira-confluence`, `devops`, `embedded`; расширено автоопределение по
  файлам-маркерам (`data-analysis` и `jira-confluence` — только явный выбор).
  NPR `ALLOWED_SECTIONS` синхронизирован, контракт-pin обновлён до BP
  `ff54781f05e9b3f945e75b602aa32cb49ded671e`; `harvest-practice-candidates`
  переспрашивает стек, если кандидат по умолчанию попадает в `common`.

- Skill [[.agents/skills/compress-project/SKILL|compress-project]] теперь явно
  предлагает сделать commit, если после компрессии изменения остались
  незакоммиченными; синхронизированы пользовательский гайд и workflow-отчёт.
- Роли «мейнтейнер» и «администратор» в workflow-отчётах объединены в одну —
  **администратор** (ведёт базу практик и стандарт); отражено в полном,
  пользовательском и административном отчётах.

- Глобальная agent policy сокращена до универсальных правил из аудита
  2026-07-07; проектные defect/playbook/promotion процессы оставлены в
  `AGENTS.md`, шаблоне нового проекта и skills. Удалены неподтверждённые
  численные лимиты и validator `instructions.chain_budget`; nested rules и
  проверка новых instruction sources приведены к фактической модели Codex;
  команда проверки использует non-interactive `codex exec`.
- [[docs/research/STRATEGIC_EVOLUTION_PLAN|Стратегический план]] актуализирован
  для schema `2`, active GitHub ruleset и следующего продуктового этапа с
  consumer-метриками; закрыт дефект №52.
- Global managed policy основного компьютера обновлена migration `0005` до
  schema `2`; backup и postcondition `managed_match` записаны в [[ACTIONS]].
- Standardization assessment теперь различает `consumer-project` и
  `rules-repository`: self-assessment стандарта возвращает `not_applicable`, а
  все consumer plan/apply блокируются до mutation; закрыт дефект №51.
- BP compatibility pin обновлён до merge A1 schema 2; contract теперь закрепляет
  не только skills, но также ADR, reference и исполняемый consumer manifest
  loader.

## v1.16.0 — 2026-07-07

### Добавлено

- Standard schema `2` и последовательный migration graph `0 → 1 → 2` для
  project metadata, global policy и project AGENTS. Один fingerprinted atomic
  apply доводит target до текущей schema, сохраняет точную migration history,
  backup и unmanaged text; missing/ambiguous graph и forged history блокируются
  regression tests.
- Исполняемый pinned compatibility contract NPR ↔ Best Practices: offline
  schema/ADR regression suite и проверка реального checkout по repository,
  commit, hashes, accepted status и retired routes; promotion skill требует
  этот gate до создания кандидата.
- GitHub governance для default branch: `.github/CODEOWNERS`, regression test
  high-trust surfaces и active ruleset `Protect main` (`id: 18603924`) с PR/
  review gate, strict `shell`/`powershell` checks и защитой истории; дефект №48
  закрыт, результат подтверждён [[docs/reviews/archive/PHASE_2_MAIN_PROTECTION_REVIEW_2026-07-07|phase-2 review]].
- Поэтапный [[docs/research/archive/NPR_BP_REMEDIATION_PLAN_2026-07-07|план исправления
  связки NPR и Best Practices]]: GitHub governance, доставка BP hardening,
  устранение stale routes, исполняемый cross-repo contract, version/migration
  NPR, наполнение BP и consumer pilot с измеримыми outcomes.
- Двухъярусная архитектура знаний ([[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture|ADR-0003]]):
  NPR — client-read-only конституция, Best Practices — единственный обратный
  поток опыта; роли администратор/пользователь. Baseline проекта обёрнут в
  managed-маркеры (schema через `<SCHEMA_VERSION>`), локальные правила снаружи и
  сохраняются; `validate-project` предупреждает о дрейфе baseline,
  `plan-migration --target project-agents` адаптирует и обновляет его. Скилл
  `harvest-project-lessons` удалён (обратный поток ушёл в Best Practices);
  `promote-project-knowledge` и `apply-promotion-candidate` стали maintainer-only
  (затвердевание практики Best Practices в правило NPR). Гайды `USE_THIS_PROJECT`
  и `AI_KNOWLEDGE_PORTABILITY` переписаны под роли.
- Promotion backlog переведён на one-file-per-candidate: добавлены каталог
  [[docs/quality/promotion-candidates/README|promotion-candidates]], генератор
  `scripts/promotion_candidates.py` с 48-битными collision-resistant ID,
  schema/duplicate validation в основном validator и отдельный regression suite.
  Legacy ID сохранены; skills harvest/apply/promote и пользовательские гайды
  синхронизированы. Реализованы кандидаты `PC-2026-625b2fcadaef` и
  `PC-2026-4eb5666c703b`, закрывающие дефекты `#43–#44`.
- Полный harvest четырёх соседних git-проектов: отчёт
  [[docs/research/archive/PROJECT_HARVEST_2026-07-06]], три очищенных `triaged`
  promotion-кандидата и два открытых дефекта текущего backlog (`#43`, `#44`).
- Компрессия проекта (Уровень 1): `scripts/compress-project.py` с обёртками
  `.sh`/`.ps1` и тестом `test-compress-project` (14 тестов). Отчёт по умолчанию,
  `--apply` делает только обратимое: перенос `Fixed`-дефектов старше
  `--fixed-max-age-days` в `DEFECTS_ARCHIVE.md`, гибридный сплит `CHANGELOG.md`
  (триггер 32 КБ, рез по границам версий, Unreleased + 5 релизов остаются),
  чистка `__pycache__`/`.DS_Store`/пустого `.trash`; WARN о `last_verified`
  старше `--stale-days`. Нацеливается на любой проект через `--root`.
- Скилл `compress-project` (Уровни 2–3): консолидация docs с показом плана и,
  по `--include-memory`, память агентов строго через отчёт → показ дублей →
  подтверждение без автоудаления. Зарегистрирован в `test-skills`, добавлены
  гайд [[docs/guides/COMPRESS_PROJECT]] и план
  [[docs/research/PROJECT_COMPRESSION_PLAN]]. Тест подключён к CI и
  macos-smoke.

### Изменено

- Bootstrap shell/PowerShell теперь создаёт обязательный
  `.project-standard.json` из manifest-driven контракта: schema, выбранный
  profile, canonical source, commit репозитория правил и даты фиксируются до
  initial commit. Git стал обязательным, поскольку без него нельзя одновременно
  создать отдельный repository и достоверно зафиксировать provenance. Добавлены
  parity/regression-проверки; закрыт дефект `#45`.
- Global migration engine теперь умеет adoption для `unmanaged_conflict`: когда
  `~/.codex/AGENTS.md` уже содержит собственные правила пользователя без markers
  (типичный новый компьютер, где велись работы), `plan-migration --target global`
  дописывает managed block **ниже** существующего текста, сохраняя его без
  изменений, с обязательным timestamped backup и тем же fingerprint/preview
  контуром. `sync-global-agents` остаётся строго read-only; писатель — только
  migration engine (см. [[docs/quality/DEFECTS|DEFECTS #28]] о риске обхода
  review/backup). Ранее `unmanaged_conflict` был `blocked` и требовал ручной
  расстановки markers. Обновлены `scripts/sync_global_agents.py`,
  `scripts/plan_migration.py`, регрессионные тесты `test-agent-sync` (8) и
  `test-migration-planner` (15) — все зелёные; синхронизированы
  [[docs/guides/PLAN_MIGRATIONS]], [[docs/guides/SYNC_GLOBAL_AGENTS]],
  [[docs/guides/SETUP_NEW_COMPUTER]] и skill `setup-new-computer`.

## v1.15.0 — 2026-07-06

### Добавлено

- Интеграция базы Best Practices в создание проекта. Skill
  [[docs/guides/CREATE_NEW_PROJECT|create-new-project]] на финальном шаге
  предлагает (opt-in) обновить или установить соседнюю базу `Best Practices` и
  применяет общие практики (`common`). Шаблон `templates/new-project/AGENTS.template.md`
  получил компактное правило: при определении стека проекта предложить подтянуть
  стековые практики через чтение `apply-best-practices/SKILL.md` из базы, а при
  её отсутствии — установить соседом `../Best Practices`. Решения пользователя
  фиксируются в `.best-practices.json` (`optout`/`applied`), чтобы отклонённые
  или уже применённые разделы не предлагались повторно. Реализовано через
  чтение skill-файла базы (без глобальной установки и без правок репозитория
  Best Practices). Тесты `test-skills`, `test-bootstrap`, `test-contract` и
  `validate-project --root . --kind rules` — 0 ошибок / 0 предупреждений.

## v1.14.0 — 2026-07-05

### Изменено

- Сжата инструкционная цепочка без потери правил: [[AGENTS]] и
  [[GLOBAL_AGENT_INSTRUCTIONS]] переформатированы так, что каждый многострочный
  пункт занимает одну строку. Цепочка `GLOBAL + AGENTS.md` уменьшилась с 300/300
  до 151/300 (запас 149), что снова открывает бюджет под будущие правила. Ни одно
  правило не удалено (пословный diff пуст), сохранены обязательные литералы
  `## Defect Tracking` и `## Knowledge Promotion` и все отличительные токены.
  Активный `~/.codex/AGENTS.md` пересинхронизирован до `managed_match`;
  `scripts/validate-project.py --root . --kind rules` — 0 ошибок / 0 предупреждений.

## v1.13.0 — 2026-07-05

### Добавлено

- [[docs/guides/MANUAL_SCRIPTS|Ручной запуск скриптов]]: пользовательский
  справочник-шпаргалка с точными командами `sh`/`.ps1`, ключевыми флагами и
  критериями «когда запускать вручную» для каждого семейства скриптов. Тест- и
  runtime-детали не дублируются (ссылки на [[docs/quality/TESTING|TESTING]] и
  [[TOOLS|TOOLS]]). Вплетён в [[INDEX]], [[docs/README|docs/README]], [[README]]
  и [[docs/guides/USE_THIS_PROJECT|USE_THIS_PROJECT]].

## v1.12.0 — 2026-07-05

### Добавлено

- Шаблон `README` для новых проектов получил секцию «Источник»: наглядная
  ссылка на стандарт `new-project-rules` (`NightMadMax/new-project-rules`) с
  отсылкой к авторитетному `.project-standard.json` за точной версией (repo и
  commit). Обновлены [[docs/guides/CREATE_NEW_PROJECT|гайд создания проекта]] и
  skill `create-new-project`; commit источника по-прежнему не дублируется в
  Markdown.

## v1.11.0 — 2026-07-03

### Исправлено

- Дефект 38: `scripts/add-agent-scope.ps1` сравнивает канонические физические
  пути, поэтому alias `/var` → `/private/var` на macOS больше не ломает
  containment-проверку; `test-agent-setup.ps1` проходит на macOS pwsh.
- Дефект 39: `check-environment.sh`/`.ps1` не требуют credential helper при
  `gh git_protocol=ssh` — SSH transport аутентифицируется ключами.
- Дефект 33 закрыт как Won't Fix: pwsh command caching в mock-git секции
  `test-bootstrap.ps1` — дефект локальной тестовой обвязки на macOS,
  полностью покрытый Windows CI.
- Дефект 34: `scripts/test-standardize-existing-project.py` запускается в CI
  на всех платформах (ubuntu и windows jobs `ci`, `macos-smoke`);
  непортабельные тесты получили skip-guards для Windows.
- Дефекты 35–37 и 40 в `scripts/standardize_existing_project.py`: symlink и
  containment guards для всех planned writes и copies (adopt-in-place и
  re-bootstrap), запрет destination внутри legacy root (включая `.git`),
  fingerprint плана теперь включает манифест файлов transfer set с
  sha256-хэшами содержимого; добавлены regression tests
  (см. [[docs/quality/DEFECTS|DEFECTS]]).

### Добавлено

- [[docs/research/PROJECT_AUDIT_2026-07-03|Повторный глубокий аудит проекта]]:
  полный regression и PowerShell прогон, live GitHub/security verification,
  проверка внешних ссылок и adversarial fixtures standardization workflow;
  дефекты 34–40 записаны в [[docs/quality/DEFECTS|DEFECTS]].
- Шаг «Консолидация журналов» в skill
  [[.agents/skills/reflect-and-record/SKILL|reflect-and-record]] и шаблон
  [[templates/new-project/DEFECTS.template|DEFECTS]]: при более чем ~30
  Fixed-записях старые переносятся в архив. Первая консолидация выполнена:
  записи 1–27 перенесены в [[docs/quality/DEFECTS_ARCHIVE|архив дефектов]].
- `.obsidian/` в генерируемый `.gitignore` (bootstrap sh/ps1,
  standardize-existing-project, локальный `.gitignore`) и заметка в
  [[docs/architecture/ARCHITECTURE|архитектуре]] о принадлежности `.obsidian/`
  уровню родительского vault (защита от повторения класса дефекта 15).
- Пакет B аудита 2026-07, правило бюджета цепочки инструкций (рекомендация 3):
  глобальные плюс проектные правила вместе ≤ ~300 непустых строк — во всех
  слоях правил; проверка `instructions.chain_budget` в `validate-project.py`
  для проектного `AGENTS.md` и `AGENTS.template.md` с регрессионными тестами.
- Правило «не запускать двух агентов одновременно в одной рабочей копии;
  параллельно — только в отдельных git worktrees» во всех слоях правил
  (рекомендация 5).
- Указания для skills (рекомендация 8): ключевые триггеры — в начало
  `description` SKILL.md, deprecated `~/.codex/prompts` не использовать — в
  [[docs/guides/AI_KNOWLEDGE_PORTABILITY|гайде о переносимости знаний]] и
  skill [[.agents/skills/apply-promotion-candidate/SKILL|apply-promotion-candidate]].
- Первый паттерн в [[docs/quality/PLAYBOOK|PLAYBOOK]]: refresh глобальной
  managed policy при `managed_drift` по паттерну engine (подтверждён дважды).

### Изменено

- Консолидированы формулировки в `GLOBAL_AGENT_INSTRUCTIONS.md` и `AGENTS.md`
  без потери правил, чтобы цепочка инструкций осталась в бюджете (299/300
  непустых строк); активный `~/.codex/AGENTS.md` обновлён по паттерну
  PLAYBOOK № 1, postcondition `managed_match` (см. [[ACTIONS]]).

### Исправлено

- Гайд [[docs/guides/USE_THIS_PROJECT|USE_THIS_PROJECT]] дополнен: Claude
  Code эквиваленты в секции knowledge promotion и workflow
  `reflect-and-record` (дефект 30).
- [[TOOLS|TOOLS.md]] ссылается на каталог скриптов в [[INDEX|INDEX]] и
  [[docs/quality/TESTING|TESTING]] и фиксирует исключения из правила
  парности `.sh`/`.ps1` (дефект 32).
- Раздел `Unreleased` нарезан в релиз `v1.10.0` (дефект 31).

## v1.10.0 — 2026-07-02

### Добавлено

- [[docs/guides/USE_THIS_PROJECT|Гайд «Как работать с этим проектом»]]:
  пользовательский вход с фразами для типовых задач и выбором workflow;
  ссылки добавлены в [[README|README]], [[INDEX|INDEX]] и
  [[docs/README|индекс документации]].
- [[docs/research/archive/PROJECT_AUDIT_2026-07|Аудит проекта — июль 2026]]:
  внутренний аудит консистентности, сверка с актуальной документацией
  Codex CLI и Claude Code, community-практики; дефекты 28–32 записаны в
  [[docs/quality/DEFECTS|DEFECTS]], рекомендации приоритизированы.
- [[docs/quality/PROMOTION_CANDIDATES|Backlog promotion candidates]] как
  staging area между project lessons и checked-in standard artifacts.
- Skills `harvest-project-lessons` (позже удалён, см. Unreleased)
  и [[.agents/skills/apply-promotion-candidate/SKILL|apply-promotion-candidate]]
  для двухшагового knowledge-promotion workflow: сначала harvesting и triage,
  затем реализация approved-кандидата в правила, шаблоны, тесты, guides или
  skills.
- [[.agents/skills/promote-project-knowledge/SKILL|promote-project-knowledge]]
  переписан в orchestration-layer над `harvest-project-lessons` и
  `apply-promotion-candidate`, чтобы не дублировать low-level workflow.
- [[docs/research/AGENT_RUNTIME_CAPABILITIES_2026|Исследование рантайм-возможностей
  Codex/Claude Code 2026]]: сверка стандарта с официальными моделями обоих
  агентов и приоритизированный план улучшений правил и настройки компьютера.
- Раздел `Done when` в шаблоне [[templates/new-project/AGENTS.template|AGENTS]]
  для явных критериев готовности и самопроверки агента.
- [[templates/new-project/PLAYBOOK.template|Шаблон Playbook]] и правило
  `Pattern Playbook` (во всех слоях правил и активном `~/.codex/AGENTS.md`):
  фиксировать проверенные удачные паттерны как success-аналог журнала дефектов.
- Раздел `Rule Authoring` (во всех слоях и `~/.codex/AGENTS.md`): как писать
  эффективные правила — компактность ~150 строк, negative-инструкции,
  command-first, группировка по задаче и тест recite-back (из community-практик).
- Правило `Reflexive Learning` (во всех слоях и `~/.codex/AGENTS.md`): после
  ошибки или поправки агент рефлексирует, обобщает урок и маршрутизирует его в
  DEFECTS / PLAYBOOK / AGENTS / promotion — замыкает петлю обучения.
- Skill [[.agents/skills/reflect-and-record/SKILL|reflect-and-record]] (канон +
  Claude-мост + регистрация в `test-skills`): вызываемая процедура рефлексии и
  записи урока для Codex и Claude Code.
- [[docs/research/AGENT_COMMUNITY_PRACTICES_2026|Исследование community-практик
  Claude Code и Codex]]: config-as-code инциденты, качество правил AGENTS.md,
  петля reflect-and-record и кандидаты на внедрение.
- Подтверждение Claude-специфики (settings keys, hooks events, `.claude/rules/`
  с `paths:`, subagents, MCP `.mcp.json`) по `code.claude.com/docs` в
  [[docs/research/AGENT_RUNTIME_CAPABILITIES_2026|исследовании]]; поправлены
  выдуманные `subagentStatusLine` и `disable-model-invocation` для субагентов.
- Immutable GitHub Actions SHA policy, weekly Dependabot updates и
  path-triggered/manual macOS smoke workflow.
- [[docs/security/THREAT_MODEL|Threat model]] bootstrap, Agent Skills, global
  policy, migrations, knowledge promotion и CI supply chain.
- Fingerprint-protected migration apply с повторной проверкой preconditions,
  atomic write, точным global backup и идемпотентным повторным запуском.
- [[ACTIONS|Журнал внешних действий]] для global marker adoption и rollback
  evidence.
- Plan-only migration engine с TSV manifest, clean-tree preconditions,
  reviewable project metadata preview и secret-safe global adoption plan.
- [[docs/architecture/PROJECT_STANDARD_SCHEMA|Schema `.project-standard.json`]]
  и [[docs/guides/PLAN_MIGRATIONS|руководство по migration planning]].
- Read-only managed-block parser и native wrappers для secret-safe
  `sync-global-agents --check/--diff` без изменения active global policy.
- [[docs/guides/SYNC_GLOBAL_AGENTS|Руководство по global policy sync]] со
  state model, marker grammar и стабильными exit codes.
- Read-only Python 3.9+ validator, native wrappers и project doctor для проверки
  profile contract, indexes, wikilinks, frontmatter, memory, paths, secrets,
  Git state и Obsidian placement.
- [[docs/guides/VALIDATE_AND_DIAGNOSE|Руководство по validator и doctor]] со
  стабильными exit codes и `report-only` режимом.
- `STANDARD_VERSION=1`, TSV contracts профилей/policy и parity-тесты, которые
  фиксируют текущие outputs до manifest-driven refactor.
- [[docs/architecture/decisions/ADR-0002-versioned-project-contract|ADR-0002]]
  о versioned contract, native bootstrap adapters и hybrid Python runtime для
  будущих validator/migrations.
- [[docs/research/STRATEGIC_EVOLUTION_PLAN|Стратегический план]] перехода к
  versioned contract, validator, global sync и безопасным migrations.
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Политика переноса знаний]] и skill
  `promote-project-knowledge`: локальные memory отделены от проверенных общих
  правил, а promotion требует источника, области применения и проверки.
- Универсальные Agent Skills `setup-new-computer` и `create-new-project` для
  Codex и Claude Code с единым каноническим workflow.
- [[docs/quality/DEFECTS|Реестр дефектов]] для обязательной фиксации найденных
  проблем и истории их исправления.
- `requirements-dev.txt` с `PyYAML` для официальных генератора и validator
  Agent Skills.

### Исправлено

- Дефект 28: активный `~/.codex/AGENTS.md` восстановлен из переносимой
  политики на обоих компьютерах (re-adoption managed markers и обновление
  managed block); операции зафиксированы в [[ACTIONS|ACTIONS]].
- Дефект 29: в [[docs/README|индекс документации]] добавлены отсутствовавшие
  research-файлы.

### Изменено

- В переносимые и проектные правила, активный `~/.codex/AGENTS.md` и шаблон
  AGENTS добавлены агент-рантайм-правила Codex: держать `AGENTS.md` компактным
  (лимит `project_doc_max_bytes`, 32 KiB), семантика `AGENTS.override.md`
  (полная замена уровня) и запрет менять `AGENTS.md`/`CLAUDE.md` в середине
  сессии (инвалидация prompt cache).
- [[docs/guides/AI_KNOWLEDGE_PORTABILITY|Политика переноса знаний]] подкреплена
  официальной позицией OpenAI о локальности memories/sessions и предпочтении
  skills вместо deprecated custom prompts.
- Workflow token остаётся read-only, checkout credentials не сохраняются, а
  CI отклоняет mutable `uses:` references до запуска project tests.
- Shell и PowerShell bootstrap теперь получают profile composition и index
  relationships напрямую из `config/profiles.tsv`; hardcoded списки артефактов
  удалены без изменения существующих profile outputs.
- Bootstrap дополняет `docs/README.md` по выбранному профилю и откатывает
  частично созданный проект при ошибке, сохраняя исходный пустой destination.
- Environment check поддерживает режимы `codex`, `claude` и `both`, поэтому
  неиспользуемый агент больше не блокирует настройку компьютера.
- Scoped agent setup отклоняет path traversal до создания каталога.
- Глобальные и проектные шаблоны правил синхронизированы и теперь содержат
  единые требования Knowledge Promotion и Defect Tracking.
- CI запускает contract-тесты Agent Skills и проверяет обязательные блоки
  переносимых инструкций.
- Общая рабочая папка теперь является единым Obsidian vault, а каждый проект —
  вложенной папкой и отдельным git/GitHub-репозиторием.
- Bootstrap больше не создаёт `.obsidian` внутри проектов; правила, шаблоны,
  руководства и проверки приведены к новой структуре.

## v1.9.0 — 2026-06-28

### Исправлено

- Shell-скрипты корректно определяют своё расположение при прямом запуске,
  через `PATH` и символическую ссылку; убраны неоднозначные GNU-зависимые
  конструкции и ложное добавление в `INDEX.md` при ошибке `grep`.
- Bootstrap проверяет каждую Git-операцию, переносимо создаёт ветку `main`,
  различает отсутствие идентичности и реальную ошибку commit и явно сообщает
  об отсутствии Git.
- Проверка окружения не обращается к credential helper, если Git отсутствует.
- PowerShell-тест больше не принимает ошибку `git status` за чистое дерево.
- PowerShell parser-check в CI возвращает ошибку при невалидном синтаксисе.

### Добавлено

- Регрессионные сценарии Git-идентичности, ошибок Git и PATH-symlink, smoke-тесты
  global/scoped agent setup и проверка PowerShell-синтаксиса без зависимостей.
- [[docs/quality/TESTING|Матрица тестирования]] и
  [[docs/reviews/CODE_REVIEW_scripts_2026-06-28|отчёт ревью скриптов]].

### CI

- Добавлены минимальные `permissions`, отмена устаревших запусков и проверки в
  Windows PowerShell 5.1 и PowerShell 7. Глобальная тестовая Git-идентичность
  удалена, чтобы не маскировать отрицательные сценарии.

## v1.8.1 — 2026-06-28

### Изменено

- В глобальные правила и шаблон `AGENTS.md` добавлено обязательное использование
  русского языка для ответов, исследований, ревью, планов и отчётов. Другой
  язык используется только по прямой просьбе пользователя; технические
  литералы сохраняются без искажения.
- Shell- и PowerShell-тесты bootstrap проверяют наличие языкового правила во
  всех создаваемых профилях.
