---
type: research
status: superseded
owner: project
last_verified: 2026-07-02
source_of_truth: repository
related:
  - "[[docs/README]]"
  - "[[docs/research/AGENT_RUNTIME_CAPABILITIES_2026]]"
  - "[[docs/research/AGENT_COMMUNITY_PRACTICES_2026]]"
  - "[[docs/quality/DEFECTS]]"
---

# Аудит проекта и направления улучшений — июль 2026

Дата: 2026-07-02. Метод: четыре параллельных исследования (внутренний аудит
консистентности, документация Codex CLI, документация Claude Code,
community-практики конца 2025 — 2026). Здесь — только тезисы, которых нет в
[[docs/research/AGENT_RUNTIME_CAPABILITIES_2026]] и
[[docs/research/AGENT_COMMUNITY_PRACTICES_2026]], либо которые их уточняют.

## 1. Внутренний аудит: состояние проекта

Проверено без замечаний: 0 битых wikilinks по 74 md-файлам; `.agents/skills/`
и `.claude/skills/` синхронизированы (8/8); все shell-скрипты проходят
`sh -n`; секретов и абсолютных путей нет;
`scripts/validate-project.py --root . --kind rules` — 0 errors / 0 warnings;
формат [[docs/quality/DEFECTS|DEFECTS]] и
[[docs/quality/PROMOTION_CANDIDATES|PROMOTION_CANDIDATES]] соблюдён.

Найденные дефекты записаны в [[docs/quality/DEFECTS]] (№ 28–32). Критичный
один: активный `~/.codex/AGENTS.md` разошёлся с переносимой копией
`GLOBAL_AGENT_INSTRUCTIONS.md`, managed markers утрачены
(`sync_global_agents.py --check` → `unmanaged_conflict`). Исправлять по
документированному пути `plan_migration.py --target global`, не ручной правкой.

## 2. Codex CLI: что изменилось в документации

- `.agents/skills/<name>/SKILL.md` — теперь **официальный** путь скиллов
  Codex (наравне с `~/.agents/skills`); вызов явный (`$skill-name`) и
  имплицитный по `description`. Custom prompts `~/.codex/prompts`
  **deprecated** — в новых проектах не использовать.
- Качество `description` в SKILL.md критично: при нехватке контекста Codex
  сокращает описания скиллов первыми — ключевые триггеры выносить в начало.
- У Codex появились **hooks** (10 событий: `SessionStart`, `PreToolUse`,
  `PostToolUse`, `Stop` и др.; `~/.codex/hooks.json` или проектный
  `.codex/hooks.json`). Trust-модель: хук требует одобрения через `/hooks`,
  привязан к хешу — хук из репозитория молча не сработает.
- Появился проектный `.codex/config.toml` (загружается только для
  trusted-проектов) — легальный аналог `.claude/settings.json`; не может
  переопределять `model_provider`, `notify`, `profile`, `otel`.
- `project_doc_max_bytes` (32 KiB) считается на **сумму** глобального файла и
  всей цепочки AGENTS.md — компактность глобального файла тоже важна.
  Проверка цепочки: `codex "Summarize current instructions."`.
- Прочее: `/import` из Claude Code (0.140), granular `approval_policy`,
  `project_doc_fallback_filenames`, нативный Windows-sandbox (experimental,
  три варианта: elevated / unelevated / WSL2), `codex exec` для CI.
- Треды/сессии между компьютерами не синхронизируются — переносимость только
  через репозиторий и per-machine `~/.codex/`; Codex cloud читает AGENTS.md
  из репозитория — ещё один аргумент держать правила в репо.
- Стандарт agents.md передан Agentic AI Foundation (Linux Foundation);
  обязательной структуры не задаёт — структура new-project-rules это
  локальная конвенция поверх открытого формата.

## 3. Claude Code: неиспользуемые возможности

- **Hooks** в `.claude/settings.json` — не используются; кандидаты:
  PostToolUse-проверка INDEX.md, PreToolUse-проверка секретов,
  Stop-напоминание о DEFECTS/reflect-and-record.
- **Settings** — нет permissions allowlist и шаблона
  `.claude/settings.json` для новых проектов.
- **Плагины** — 8 скиллов можно упаковать в plugin
  (`.claude-plugin/plugin.json`) для переносимости и версионирования.
- Bridge-паттерн `.claude/skills/ → .agents/skills/` работает, но требует
  ручной синхронизации; Claude Code видит только краткую ссылку-мост.
- Path-scoped rules (`.claude/rules/`) и шаблоны субагентов
  (`.claude/agents/*.md`) — существуют, для текущего масштаба не нужны.

## 4. Community-практики: тезисы

- Модели надёжно удерживают ~150–200 инструкций на контекст; считать нужно
  **суммарную цепочку** (глобальный + проектный AGENTS.md), а не один файл.
  Текущая цепочка (~130 + ~160 строк) у верхней границы.
- Консенсус 2026: критичные правила переводить из текста в hooks
  («enforcement layer») — не полагаться, что агент «вспомнит» правило.
  Для markdown-only solo-проекта сигнала на немедленное внедрение нет.
- Против разрастания lessons-файлов: прогрессивное раскрытие (в AGENTS.md —
  указатель, детали в файлах) и регулярная **консолидация**; Fixed-раздел
  DEFECTS при N > ~30 записей сжимать в архив (сейчас 27 — сигнал близко).
- Уточнение к правилу «negative-инструкции эффективнее»: если конкретное
  negative-правило игнорируется, помогает preference-форма
  («Prefer Y over X»), затем hook.
- Два агента на одном репо: последовательно — можно; одновременно в одной
  рабочей копии — анти-паттерн (`.git/index.lock`, stale reads); параллельно
  только в отдельных git worktrees. Доминирующий роль-паттерн:
  «Claude implements → Codex reviews».
- Obsidian + git: в текущей модели (vault — родительский каталог, проекты —
  вложенные репо) `.obsidian/` в проектные репо не попадает, и большинство
  community-проблем неприменимы; защитные строки `.obsidian/`, `.DS_Store`,
  `Thumbs.db` в шаблонном `.gitignore` закрывают сценарий дефекта № 15.
- Собственный validator (wikilinks, frontmatter, secrets) — впереди
  community-практики; готового CI-инструмента для wikilinks у сообщества нет.
  Единственный реальный пробел — проверка внешних URL (lychee, report-only).
- Архитектура `.project-standard.json` + migration engine — прямой аналог
  Copier/cruft; миграция на них не оправдана. Полезные заимствования:
  drift-check в сгенерированных проектах и diff old/new рендера шаблонов.

## 5. Приоритизированные рекомендации

Внедрять сейчас (дёшево, есть сигнал):

1. Исправить drift `~/.codex/AGENTS.md` через migration workflow (дефект № 28).
2. Закрыть дефекты консистентности № 29–32 (индексы, гайд, CHANGELOG, TOOLS).
3. Бюджет суммарной цепочки инструкций (глобальный + проектный ≤ ~250–300
   строк) — правило + проверка в существующем validator.
4. Шаг консолидации DEFECTS/PLAYBOOK в `reflect-and-record`
   (архив Fixed при N > ~30).
5. Правило-однострочник: «Не запускать двух агентов одновременно в одной
   рабочей копии; параллельно — только в отдельных git worktrees».
6. `.obsidian/`, `.DS_Store`, `Thumbs.db` в шаблонном `.gitignore` + заметка
   о слоях vault в архитектуре.
7. lychee (report-only CI) для внешних URL в research-файлах.
8. В правилах о скиллах: не использовать `~/.codex/prompts` (deprecated);
   ключевые триггеры — в начало `description`.

Записать как идеи (ждать сигнала): Stop-hook напоминание о
reflect-and-record; шаблон `.claude/settings.json` с permissions;
упаковка скиллов в Claude-plugin; проектный `.codex/config.toml` и
`.codex/hooks.json`; stale-`last_verified` проверка; drift-check в
сгенерированных проектах; diff-подход к миграциям шаблонов; роль-паттерн
«Claude implements → Codex reviews»; Windows-sandbox заметка в
setup-new-computer.

Не подходит (solo, по сигналу): markdownlint-cli2, pre-commit framework,
миграция на Copier/cruft, оркестраторы двух агентов, obsidian-git
auto-commit, path-scoped rules и субагенты на текущем масштабе.

## Источники

Codex: [AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md),
[Skills](https://developers.openai.com/codex/skills),
[Hooks](https://developers.openai.com/codex/hooks),
[Config reference](https://developers.openai.com/codex/config-reference),
[Changelog](https://developers.openai.com/codex/changelog),
[Windows](https://developers.openai.com/codex/windows),
[agents.md](https://agents.md/).
Claude Code: [Memory](https://code.claude.com/docs/en/memory.md),
[Skills](https://code.claude.com/docs/en/skills.md),
[Hooks](https://code.claude.com/docs/en/hooks-guide.md),
[Settings](https://code.claude.com/docs/en/settings.md),
[Plugins](https://code.claude.com/docs/en/plugins.md).
Community: [Hooks as enforcement layer](https://ranjankumar.in/hooks-policy-as-code-agent-enforcement),
[Stop AI agents forgetting rules](https://serenitiesai.com/articles/claude-code-ignoring-instructions-agents-md-fix),
[lychee-action](https://github.com/lycheeverse/lychee-action),
[Copier updating](https://copier.readthedocs.io/en/stable/updating/),
[Claude Code + Codex together](https://codex.danielvaughan.com/2026/03/27/using-claude-code-and-codex-together/),
[Worktrees for parallel agents](https://www.augmentcode.com/guides/git-worktrees-parallel-ai-agent-execution),
[Obsidian and Git](https://rob.cogit8.org/posts/2025-03-25-obsidian-git-quick-setup-for-developers/).
