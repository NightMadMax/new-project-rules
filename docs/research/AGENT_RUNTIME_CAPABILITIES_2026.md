---
type: research
status: active
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[PROJECT]]"
  - "[[GLOBAL_AGENT_INSTRUCTIONS]]"
  - "[[docs/research/MUST_HAVE_PROJECT_TOOLING_2026|MUST_HAVE_PROJECT_TOOLING_2026]]"
  - "[[docs/research/STRATEGIC_EVOLUTION_PLAN|STRATEGIC_EVOLUTION_PLAN]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY|AI_KNOWLEDGE_PORTABILITY]]"
  - "[[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]]"
---

# Research: рантайм-возможности агентов (Codex и Claude Code) 2026

## Question

Что ещё можно улучшить в `new-project-rules` (правила ведения проекта и
настройка компьютера), чтобы агенты Codex и Claude Code работали максимально
эффективно через память, документацию, учёт ошибок и переиспользуемые навыки?

## Method and Evidence

Исследование проведено 2026-06-30 двумя параллельными агентами по первичным
источникам.

- Codex — подтверждено по официальной документации `developers.openai.com/codex`
  (надёжно).
- Claude Code — часть деталей не подтверждена первоисточником и помечена ниже
  как «проверить по `code.claude.com/docs`», чтобы не зафиксировать в стандарте
  непроверенные ключи настроек.

Ключевые источники Codex:
[AGENTS.md](https://developers.openai.com/codex/guides/agents-md),
[config-reference](https://developers.openai.com/codex/config-reference),
[MCP](https://developers.openai.com/codex/mcp),
[memories](https://developers.openai.com/codex/memories),
[cloud environments](https://developers.openai.com/codex/cloud/environments),
[best-practices](https://developers.openai.com/codex/learn/best-practices),
[custom-prompts (deprecated)](https://developers.openai.com/codex/custom-prompts).

## Findings

### Совпадает со стандартом (подтверждено первоисточниками)

- Единый `AGENTS.md` + `CLAUDE.md` = `@AGENTS.md` — это официальная модель
  совместимости. Import-паттерн выбран сознательно вместо symlink ради
  переносимости macOS/Windows — корректно.
- Skills как переносимый формат — OpenAI пометила custom prompts (`~/.codex/prompts`)
  deprecated и двигает Skills как первичный механизм переиспользования.
- Запрет коммита памяти — OpenAI прямо пишет: memories/sessions локальны, не
  синхронизируются между машинами, не source of truth.
- Supply-chain hardening, DEFECTS-дисциплина — согласуются с моделью
  «AGENTS.md как живой артефакт».

### Codex: уточнения и новое (надёжно)

1. Терминология approval устарела. Актуально: `approval_policy`
   (`untrusted`/`on-request`/`never`) × `sandbox_mode`
   (`read-only`/`workspace-write`/`danger-full-access`). `--full-auto` =
   `on-request` + `workspace-write`; `network_access` в `workspace-write`
   выключен по умолчанию.
2. `~/.codex/config.toml` поддерживает именованные профили (`model` + `sandbox`
   + `approval` + MCP), выбор `--profile`. Приоритет: CLI > профиль > config >
   дефолты.
3. Лимит чтения AGENTS.md — `project_doc_max_bytes`, по умолчанию **32 KiB**;
   при превышении инструкции молча обрезаются.
4. `AGENTS.override.md` **полностью заменяет** уровень, а `AGENTS.md`
   конкатенируется с родителями.
5. MCP в Codex: `[mcp_servers.<name>]` в config.toml; ключи `command`/`args`/`env`
   или `url`/`bearer_token_env_var`, `enabled_tools`/`disabled_tools`,
   `approval_mode`. Токены только через env.
6. Cloud environments: setup-скрипты ставят зависимости; `export` в setup-фазе
   **не виден** фазе агента; секреты доступны только setup-скрипту; сеть в фазе
   агента выключена по умолчанию.
7. Не менять AGENTS.md в середине сессии — это инвалидирует кэшируемый префикс
   промпта (prompt caching).
8. Рекомендованный элемент AGENTS.md — раздел критериев готовности «Done when».

### Claude Code: к проверке по `code.claude.com/docs`

Подтверждены концептуально, но конкретные ключи не сверены с первоисточником и
требуют проверки перед фиксацией в стандарте:

- Иерархия `CLAUDE.md` (managed / user `~/.claude` / project / `CLAUDE.local.md`
  / subdirectory) и возможные path-scoped rules `.claude/rules/` с `paths:`.
- `.claude/settings.json` / `settings.local.json`, блок `permissions`
  (`allow`/`deny`/`ask`), env, model.
- Hooks: `PreToolUse`/`PostToolUse`/`SessionStart`/`UserPromptSubmit`/`Stop`
  и т.д.; блокирующий `PreToolUse` через ненулевой exit code.
- Subagents `.claude/agents/*.md` с frontmatter (`name`, `description`, `tools`,
  `model`).
- MCP через `.mcp.json` (project) и user scope.
- Конкретные ключи `effortLevel`, `autoMemoryEnabled`, `subagentStatusLine`,
  событие `InstructionsLoaded`, номер версии — НЕ подтверждены, не вносить без
  проверки.

## Conclusion

Архитектурное ядро стандарта соответствует официальным моделям обоих агентов.
Основной потенциал — добавить нативные рантайм-механизмы агентов, которых пока
нет в шаблонах проекта и в настройке компьютера.

### План улучшений по приоритетам

**Приоритет 1 — грунтованные, безопасные (внедряем первыми):**

1. Обновить терминологию Codex approval/sandbox в гайдах и
   [[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]].
2. Зафиксировать лимит AGENTS.md 32 KiB и правило «короткий AGENTS.md» +
   семантику `AGENTS.override.md` (replace) в
   [[GLOBAL_AGENT_INSTRUCTIONS]] и [[AGENTS]].
3. Добавить правило «не менять AGENTS.md/CLAUDE.md в середине сессии»
   (prompt cache).
4. Добавить раздел «Done when / критерии готовности» в шаблон
   [[templates/new-project/AGENTS.template|AGENTS.template]].
5. Сослаться на официальную позицию OpenAI о локальности памяти в
   [[docs/guides/AI_KNOWLEDGE_PORTABILITY|AI_KNOWLEDGE_PORTABILITY]].
6. Подтвердить, что Skills — единый формат; custom prompts deprecated.

**Приоритет 2 — новые возможности (после сверки Claude-специфики):**

7. Шаблон `~/.codex/config.toml` с профилями (review/dev) и `network_access=false`.
8. Шаблон `.claude/settings.json` с security-first permissions (deny `.env*`,
   ключи, force-push).
9. Hooks под кейс проекта (защита критичных путей, авто `sh -n`, напоминание о
   DEFECTS).
10. MCP-секция в [[templates/new-project/INTEGRATIONS.template|INTEGRATIONS.template]].
11. Codex cloud environments в шаблоне operations/ENVIRONMENTS.
12. Subagents `.claude/agents/` (validator, security-reviewer).

**Приоритет 3 — концептуальный пробел:**

13. Журнал проверенных удачных паттернов («обучение на успехах», параллель к
    DEFECTS) — раздел в AGENTS.md или `docs/quality/PLAYBOOK.md`.
</content>
</invoke>
