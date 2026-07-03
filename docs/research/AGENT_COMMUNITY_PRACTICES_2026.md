---
type: research
status: active
owner: project
last_verified: 2026-06-30
source_of_truth: repository
related:
  - "[[PROJECT]]"
  - "[[docs/research/AGENT_RUNTIME_CAPABILITIES_2026|AGENT_RUNTIME_CAPABILITIES_2026]]"
  - "[[docs/security/THREAT_MODEL|THREAT_MODEL]]"
  - "[[docs/quality/DEFECTS|DEFECTS]]"
  - "[[templates/new-project/AGENTS.template|AGENTS.template]]"
---

# Research: community-практики Claude Code и Codex 2026

## Question

Что наработало сообщество практиков (вне официальной документации Anthropic и
OpenAI), что стоит добавить в фреймворк `new-project-rules` — правила, шаблоны,
skills, чек-листы?

## Method and Evidence

Исследование 2026-06-30 двумя параллельными агентами по community-источникам:
Reddit, Hacker News, dev.to, Medium, инженерные блоги, GitHub awesome-репозитории,
security research. Findings отфильтрованы от того, что уже подтверждено в
[[docs/research/AGENT_RUNTIME_CAPABILITIES_2026|официальном исследовании]] и уже
внедрено. Агент по Codex-сообществу завершил основную часть поиска, но не выдал
финальный отчёт (зависание); его собранные результаты учтены из рабочего журнала.

Достоверность: **[A]** — несколько независимых источников / security research;
**[B]** — один развёрнутый практический источник; **[C]** — единичное мнение.

## Findings

### Безопасность (наиболее ценное)

- **«Config-файлы = исполняемый код» [A].** Реальные инциденты, срабатывающие до
  trust-диалога: RCE через `SessionStart`-hook в `.claude/settings.json`
  (CVE-2025-59536); кража API-ключа через `ANTHROPIC_BASE_URL` в settings
  (CVE-2026-21852); MCP consent bypass через `enableAllProjectMcpServers`; RCE в
  Codex CLI на Windows через prompt injection (подмена Node.js runtime в
  workspace); самостоятельное отключение sandbox агентом; `rm -rf ~` при cleanup.
  Источники: research.checkpoint.com, cymulate.com, csoonline.com, github.com/openai/codex.
- **Веб-результаты и контент репозитория — недоверенные [A].** Prompt injection /
  goal hijacking — риск №1 в OWASP Top 10 for Agentic Applications 2026. Совет:
  deny на `.env`/`curl`-exfil, одобрять только проверенные MCP, output-фильтрация.

### Качество правил в AGENTS.md/CLAUDE.md [A]

- Потолок **~150 строк** (эмпирика на 2500+ репозиториев): за порогом стоимость
  инференса +20–23% без выигрыша, нижние правила игнорируются. Совпадает с
  официальным «target under 200 lines».
- **Negative-инструкции эффективнее positive**: «use pnpm, not npm», «don't use
  axios — use fetch» вместо «write clean code».
- **Command-first**: точные команды (`ruff check . && pytest -v`) вместо прозы.
- **Explicit closure / Done-when** через коды выхода (уже внедрено в шаблон).
- **Task-organized секции** («When writing code / reviewing / releasing»).
- Антипаттерны: проза без команд, размытые директивы («be careful»),
  противоречивые приоритеты, aspirational-правила без связи с кодом.
- Тест «recite-back»: попросить агента пересказать правила; не может — слишком
  длинно/не читается.
  Источники: blakecrosley.com, hboon.com, aihackers.net, aicodex.to, techsy.io.

### Обучение агента и анти-повторение ошибок

- **Цикл reflect-and-record [B]**: после ошибки — *Reflect → Abstract →
  Generalize → Write*. Соединяет [[docs/quality/DEFECTS|DEFECTS]],
  [[templates/new-project/PLAYBOOK.template|PLAYBOOK]] и promotion в одну петлю.
  Источники: dev.to/aviadr1, addyosmani.com/blog/self-improving-agents.
- **META-секция «как писать правила» [B]**: NEVER/ALWAYS, причина → правило,
  концизность — чтобы качество правил росло, а не деградировало.
- **CLAUDE.md как код [B]**: владелец + периодический ревью, удаление неактуальных
  и противоречивых правил.

### Workflow и контекст

- **explore → plan → [human gate] → execute → commit [A/B]**: точка контроля
  человека ставится между Plan и Execute, не раньше (исследование read-only —
  дёшево).
- **Деградация при ~2/3 контекста [A]**: триггер для `/clear`, `/compact` или
  делегирования исследования субагенту (возвращается только summary).
- **worktrees для параллельных агентов [A]** (Codex app и Claude): отдельный git
  worktree на задачу; полезно при множестве независимых задач.

## Conclusion

Большинство сильных community-инсайтов — это **улучшения текста правил и
безопасности**, кросс-агентные и дешёвые, что соответствует принципам стандарта
(единый источник, по сигналу, кросс-платформенность).

### Кандидаты на внедрение (решение пользователя)

1. **(I) Security «config = исполняемый код»** + инспекция config-каталогов
   (`.claude/`, `.mcp.json`, `.vscode/`, `.codex/`) до открытия legacy/чужого
   репозитория. В [[docs/security/THREAT_MODEL|THREAT_MODEL]] и skills
   `assess-existing-project`/`standardize-existing-project`. Достоверность [A].
2. **(II) Раздел «как писать эффективные правила»** в шаблоне AGENTS и гайде:
   ≤150 строк, negative-инструкции, command-first, task-organized, recite-back.
   Достоверность [A].
3. **(III) reflect-and-record** как правило, связывающее DEFECTS → обобщение →
   PLAYBOOK/promotion. Достоверность [B] — проверить на одном проекте.

### Отложено по принципу «по сигналу»

- worktrees, side-chat, ролевые субагенты, MCP-минимализм — низкий сигнал для
  соло/markdown-сетапа; вернуться при появлении командного/кодового проекта.
</content>
