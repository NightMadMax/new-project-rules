---
name: setup-new-computer
description: Настраивает новый macOS- или Windows-компьютер для работы с общим Obsidian vault, GitHub, Codex и Claude Code по правилам new-project-rules. Использовать, когда пользователь просит подготовить, подключить, проверить или перенести рабочее окружение на новый компьютер; не использовать для создания отдельного проекта.
---

# Настройка нового компьютера

Подготовить компьютер по каноническим правилам проекта, сохраняя существующие
пользовательские настройки и не устанавливая программы без разрешения.

## Найти источник правил

1. Найти корень `new-project-rules`: каталог должен содержать `AGENTS.md`,
   `GLOBAL_AGENT_INSTRUCTIONS.md`, `scripts/` и `docs/guides/`.
2. Сначала искать корень над каталогом этого skill. Если skill установлен
   отдельно, найти существующий clone; при его отсутствии клонировать
   `NightMadMax/new-project-rules` внутрь родительского Obsidian vault.
3. Полностью прочитать корневой `AGENTS.md` и
   `docs/guides/SETUP_NEW_COMPUTER.md`. Они имеют приоритет над этим workflow.

## Выполнить настройку

1. Определить ОС, домашний каталог, расположение общего Obsidian vault и clone
   `new-project-rules`. Не считать вложенную папку проекта отдельным vault.
2. Определить agent mode: `codex`, `claude` или `both`. По умолчанию использовать
   `both`, но не требовать неиспользуемого агента, если пользователь выбрал один.
3. Запустить read-only doctor в выбранном режиме:
   - macOS/Linux: `./scripts/project-doctor.sh --root <rules-root> --agent-mode <mode>`;
   - Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\project-doctor.ps1 -Root <rules-root> -AgentMode <mode>`,
     если системная policy блокирует прямой запуск. Не менять execution policy.
   Doctor всегда проверяет окружение; при доступном Python 3.9+ он дополнительно
   валидирует rules repository, Git state и Obsidian placement.
4. Для каждого обязательного отсутствующего инструмента объяснить пакет,
   источник и область установки, затем получить разрешение. Не устанавливать
   рекомендуемый инструмент ради удобства.
5. Проверить `gh auth status`, безопасный Git credential helper и Git identity.
   Не печатать токены. Если `user.name` или `user.email` отсутствуют, получить
   предпочтительные значения пользователя; для email предложить GitHub
   `noreply`.
6. Запустить из корня правил `scripts/setup-global-agents.sh` или
   `scripts/setup-global-agents.ps1`. При конфликте не перезаписывать файлы:
   сравнить правила и запросить решение пользователя.
7. Проверить read-only состояние global policy и показать secret-safe план:
   - macOS/Linux: `./scripts/sync-global-agents.sh --check`, затем
     `./scripts/sync-global-agents.sh --diff --report-only`;
   - Windows: `.\scripts\sync-global-agents.ps1 -Check`, затем
     `.\scripts\sync-global-agents.ps1 -Diff -ReportOnly`.
   `legacy_exact` означает, что содержимое совпадает, но managed markers ещё не
   установлены. `unmanaged_conflict` означает, что в файле уже есть собственные
   правила пользователя без markers. Оба состояния adoptable подтверждаемой
   миграцией (для conflict managed block дописывается ниже существующих правил,
   сохраняя их). Не добавлять markers вручную и не изменять active file здесь:
   запись выполняет отдельный migration workflow на шаге 8.
8. Построить отдельный global adoption plan без записи:
   - macOS/Linux: `./scripts/plan-migration.sh --plan --target global --report-only`;
   - Windows: `.\scripts\plan-migration.ps1 -Plan -Target global -ReportOnly`.
   Зафиксировать blockers и fingerprint. После явного подтверждения пользователя
   применить только неизменившийся plan через `--apply --fingerprint <value>
   --yes` или `-Apply -Fingerprint <value> -Confirm`. Не редактировать markers
   вручную; сохранить путь созданного backup в отчёте.
9. Проверить, что Obsidian установлен и родительская рабочая папка открыта как
   единый vault. Не создавать `.obsidian` внутри репозиториев и не менять UI
   вслепую.

## Проверить результат

1. Повторно запустить doctor в том же agent mode.
2. Зафиксировать состояние sync. `managed_match` полностью соответствует
   managed-block contract; `legacy_exact` подтверждает правильное содержимое,
   но оставляет marker migration отдельным следующим шагом. Убедиться, что
   `~/.claude/CLAUDE.md` содержит только `@~/.codex/AGENTS.md`.
3. Проверить `gh auth status`, Git identity, credential helper, remote и чистоту
   clone правил.
4. Сообщить отдельно: что настроено, что уже было настроено и какие ручные шаги
   остались. Не объявлять успех при непройденной обязательной проверке.
