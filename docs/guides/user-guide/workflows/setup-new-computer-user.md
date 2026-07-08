---
type: guide
status: active
owner: project
last_verified: 2026-07-08
source_of_truth: repository
related:
  - "[[docs/guides/user-guide/workflows/README|Каталог workflow]]"
  - "[[docs/guides/SETUP_NEW_COMPUTER|SETUP_NEW_COMPUTER]]"
  - "[[docs/guides/SYNC_GLOBAL_AGENTS|SYNC_GLOBAL_AGENTS]]"
  - "[[docs/guides/PLAN_MIGRATIONS|PLAN_MIGRATIONS]]"
---

# Настройка нового компьютера — workflow пользователя

Один раз на каждой новой машине. Каждый шаг можно сделать **двумя маршрутами** —
🗣 попросить агента словами или ⌨ запустить скрипт вручную. Результат один.
Визуальная версия: [setup-new-computer-user.html](assets/setup-new-computer-user.html).

**Результат:** компьютер готов — инструменты установлены, GitHub авторизован,
общий vault открыт, глобальные правила агентов подключены и проверены.

## Шаги

1. **Установить программы.** — Где: терминал/система
   - 🗣 Агенту: *«Проверь, каких инструментов не хватает (Git, gh, Obsidian,
     Codex/Claude Code), объясни и установи с моего разрешения»*.
   - ⌨ Вручную: установить через пакетный менеджер; проверить `git --version`,
     `gh --version`. На Windows — PowerShell; Python 3.9+ опционален.
   - Готово, когда команды отвечают версиями.

2. **Авторизовать GitHub.** — Где: терминал
   - 🗣 Агенту: *«Авторизуй GitHub тем же аккаунтом с доступом к NightMadMax»*.
   - ⌨ Вручную: `gh auth login`, затем `gh auth status`.

3. **Клонировать набор правил.** — Где: рабочая папка vault
   - 🗣 Агенту: *«Клонируй new-project-rules в общую рабочую папку»*.
   - ⌨ Вручную: `gh repo clone NightMadMax/new-project-rules`. Локально папку
     можно назвать `Правила для нового проекта`; имя репозитория остаётся
     `new-project-rules`.

4. **Подключить глобальные правила агентов.** — Где: папка `Правила для нового проекта`
   - 🗣 Агенту: открыть агента в этой папке; *«Настрой новый компьютер, режим
     codex, ничего не устанавливай без разрешения»* · `/setup-new-computer`
     (Codex — `$setup-new-computer`).
   - ⌨ Вручную: `./scripts/project-doctor.sh --root . --agent-mode codex`,
     `./scripts/setup-global-agents.sh`, `./scripts/sync-global-agents.sh --check`
     (на Windows — `.ps1`).
   - Готово, когда созданы `~/.codex/AGENTS.md` и `~/.claude/CLAUDE.md`; sync
     показывает корректное adoption-состояние.

5. **Открыть общую папку как Obsidian vault.** — Где: Obsidian
   - ⌨ Только вручную (агент не может): **Open folder as vault** → выбрать
     **родительскую** рабочую папку. Вложенные проекты как отдельные vault не
     открывать.

6. **Проверить и применить миграцию правил.** — Где: папка `Правила для нового проекта`
   - 🗣 Агенту: *«Построй план миграции глобальных правил и покажи; применяй
     только после моего подтверждения fingerprint»*.
   - ⌨ Вручную: `./scripts/plan-migration.sh --plan --target global --report-only`,
     затем `--apply --target global --fingerprint "<64-hex>" --yes`.
   - Готово, когда повторный `--check` показывает `managed_match`, backup сохранён.

**Безопасность:** любой маршрут — агент сначала объясняет, что и зачем
ставит/меняет, и ждёт разрешения. Setup не перезаписывает существующие правила:
при конфликте показывает состояние и предлагает подтверждаемую миграцию.
