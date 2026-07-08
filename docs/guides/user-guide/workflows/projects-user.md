---
type: guide
status: active
owner: project
last_verified: 2026-07-08
source_of_truth: repository
related:
  - "[[docs/guides/user-guide/workflows/README|Каталог workflow]]"
  - "[[docs/guides/CREATE_NEW_PROJECT|CREATE_NEW_PROJECT]]"
  - "[[docs/guides/ASSESS_EXISTING_PROJECT|ASSESS_EXISTING_PROJECT]]"
  - "[[docs/guides/STANDARDIZE_EXISTING_PROJECT|STANDARDIZE_EXISTING_PROJECT]]"
  - "[[docs/guides/VALIDATE_AND_DIAGNOSE|VALIDATE_AND_DIAGNOSE]]"
  - "[[docs/guides/COMPRESS_PROJECT|COMPRESS_PROJECT]]"
---

# Работа с проектами — карта действий пользователя

Что можно делать с проектами по стандарту. «Создать проект» — процесс (шаги
ниже); остальное — независимые действия-возможности. Визуальная версия:
[projects-user.html](assets/projects-user.html).

**Почему не один workflow.** Линейная модель «шаг за шагом» подходит только для
процессов (создание проекта, настройка компьютера). «Оценить»,
«стандартизировать», «валидировать», «сжать» — самостоятельные действия, поэтому
здесь карта: у каждого свой «когда» и «чем запускается». Почти всё живёт в папке
`Правила для нового проекта`.

## Процесс: создать новый проект

Где: открыть агента в папке `Правила для нового проекта` (bootstrap использует её
commit как проверяемый `source_commit`).

- **Запросить создание — два маршрута:**
  - 🗣 Агенту: *«Создай новый проект „Название“ в папке `<путь>`, профиль
    software, приватный GitHub-репозиторий»* · `/create-new-project`. Профиль по
    умолчанию `software` (есть `minimal`, `operated`, `all`).
  - ⌨ Вручную: `./scripts/bootstrap-new-project.sh "<путь>" "Название" software`
    (или `.ps1` на Windows).
- Агент разворачивает структуру: папка внутри общего vault как отдельный
  git-репозиторий; `AGENTS.md`/`CLAUDE.md`, `README`, `PROJECT`, `INDEX`; только
  подходящие профилю документы.
- Публикация и проверка: git init → отдельный GitHub-репозиторий → первый commit
  и push (local-only — без GitHub). Проверяет `.project-standard.json`, bootstrap,
  git status, wikilinks.
- Заполнить стартовые документы: `PROJECT` (цель/scope/non-goals), `AGENTS →
  Commands` (только проверенные команды), `INDEX` (только существующие файлы).

## Каталог: остальные действия с проектами

| Действие | Когда применять | Чем запускается |
|---|---|---|
| 🔎 Оценить существующий проект (read-only) | Понять разрыв legacy со стандартом без изменения файлов | *«Оцени этот проект относительно стандарта»* · `/assess-existing-project` |
| 🧭 Стандартизировать проект | Привести legacy к стандарту — на месте или пересобрать | *«Предложи стратегию стандартизации»* · `/standardize-existing-project` |
| ✅ Проверить и продиагностировать (read-only) | Убедиться, что проект/окружение соответствуют стандарту | `python3 scripts/validate-project.py` · `./scripts/project-doctor.sh` |
| 🗜️ Сжать «мусор» проекта | Проект разросся; уборка перед релизом | *«Сожми накопившийся мусор проекта»* · `/compress-project` |
| 📥 Подтянуть практики Best Practices | Определён стек; применить готовые практики (в своём проекте) | *«Подтяни практики под стек»* · `/apply-best-practices` |
| 🔄 Синхронизировать глобальные правила (read-only) | Проверить состояние global policy, увидеть diff | `./scripts/sync-global-agents.sh --check` · `--diff --report-only` |
| 🧱 Спланировать миграцию правил | Применить изменения global/project policy контролируемо | `./scripts/plan-migration.sh --plan --report-only`, apply — по fingerprint |
| 📝 Зафиксировать урок / дефект | Нашёл баг или удачный приём (в своём проекте) | *«Зафиксируй урок»* · `/reflect-and-record` |

Каждое действие при необходимости раскрывается в собственный детальный workflow.
