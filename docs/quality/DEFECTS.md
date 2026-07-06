---
type: defect-log
status: active
owner: project
last_verified: 2026-07-06
related:
  - "[[docs/README]]"
  - "[[docs/quality/TESTING]]"
---

# Дефекты

Обнаруженные дефекты не удаляются: после исправления запись переносится в
соответствующий раздел с датой и commit.

## Open

| # | Title | Discovered | Component | Description |
|---|---|---|---|---|

## Fixed

Записи, исправленные до релиза `v1.10.0` (№ 1–3, 5–27), перенесены при
консолидации в [[docs/quality/DEFECTS_ARCHIVE|архив дефектов]] без изменения
содержимого. Нумерация сквозная и не переиспользуется.

| # | Title | Discovered | Fixed | Commit | Root Cause |
|---|---|---|---|---|---|
| 28 | Активный `~/.codex/AGENTS.md` разошёлся с переносимой копией, managed markers утрачены | 2026-07-02 | 2026-07-02 | см. [[ACTIONS]] | После adoption 2026-06-30 активный файл был перезаписан старой редакцией без markers (вероятно, старый `setup-global-agents` на другом компьютере; root cause подтвердить). Исправлено: user-reviewed копия portable → active, затем migration `0002` (fingerprint `18a73ff1…f063d`), postcondition `managed_match`. |
| 29 | `docs/README.md` не содержит два research-файла | 2026-07-02 | 2026-07-02 | `7fb88eb` | Секция «Исследования» не пополнялась при добавлении research-файлов; ссылки на AGENT_RUNTIME_CAPABILITIES_2026 и AGENT_COMMUNITY_PRACTICES_2026 добавлены. |
| 30 | `USE_THIS_PROJECT.md` неполон | 2026-07-02 | 2026-07-02 | `21f3cdf` | Гайд писался до финализации набора skills: секция knowledge promotion не получила Claude Code эквиваленты, а `reflect-and-record` выпал из перечня workflows. Добавлены `/`-вызовы и секция 9 с фразами и таблицей выбора. |
| 31 | CHANGELOG `Unreleased` разросся и отстаёт | 2026-07-02 | 2026-07-02 | `21f3cdf` | Пять циклов работы после `v1.9.0` не нарезались в релиз, и записи о новых артефактах отставали. Нарезан `v1.10.0 — 2026-07-02`, добавлены записи о гайде и дефектах 28–29. |
| 32 | `TOOLS.md` не каталогизирует большинство скриптов | 2026-07-02 | 2026-07-02 | `21f3cdf` | Правило про TOOLS.md выполнялось только для Python/PowerShell runtime. Добавлен раздел `Script entry points`: ссылка на [[INDEX]]/[[docs/quality/TESTING|TESTING]] как авторитетные каталоги, семейства скриптов и явное исключение из правила парности `.sh`/`.ps1`. |
| 34 | Standardization regression suite не запускается в CI | 2026-07-03 | 2026-07-03 | `fcf16e7` | Suite добавлялся в локальную матрицу TESTING, но шаг в workflows не создавался. Подключён к ubuntu/windows jobs `ci` и `macos-smoke`; непортабельные тесты получили skip-guards (POSIX wrapper на Windows, symlink fixtures без прав на symlink). |
| 38 | PowerShell scoped-agent test падает локально на macOS из-за `/var` и `/private/var` | 2026-07-03 | 2026-07-03 | `83d5e11` | Containment-проверка сравнивала строки без резолва symlink-предков (`/var` → `/private/var`). Добавлен `Get-CanonicalExistingPath` (chdir + getcwd даёт физический путь на Unix); root, probe и directory сравниваются в канонической форме. `test-agent-setup.ps1` проходит на macOS pwsh (31/31). |
| 39 | Environment check требует HTTPS credential helper при SSH Git transport | 2026-07-03 | 2026-07-03 | `83d5e11` | Проверка не различала transport. Теперь при `gh git_protocol=ssh` и пустом `credential.helper` выводится `[ ok ]` (SSH аутентифицируется ключами); для HTTPS/неизвестного transport поведение прежнее. Обе ветки проверены в sh и pwsh с изолированным git-конфигом. |
| 35 | Standardization apply пишет через symlink за пределы проекта | 2026-07-03 | 2026-07-03 | `3ace8ca` | Планируемые writes никогда не проверялись на symlink/containment. Добавлен `unsafe_write_reason()`: план блокируется, а `apply_plan()` отказывает, если путь выходит за root или проходит через symlink; regression test с `INDEX.md` → внешний файл. |
| 36 | Re-bootstrap разыменовывает symlink и копирует внешний файл | 2026-07-03 | 2026-07-03 | `3ace8ca` | `copy_transfer_item()` использовал `shutil.copy2()` без проверки symlink. Теперь план блокируется при symlink в transfer set (`build_transfer_manifest()`), а apply дополнительно отказывает копировать symlink и проверяет containment target. |
| 37 | Re-bootstrap fingerprint не защищает содержимое transfer set | 2026-07-03 | 2026-07-03 | `3ace8ca` | Fingerprint включал только имена top-level paths. В payload добавлен `transfer_manifest` — полный список файлов с sha256 содержимого; изменение файла после review даёт fingerprint mismatch, что покрыто regression test. |
| 40 | Re-bootstrap разрешает destination внутри legacy repo и `.git` | 2026-07-03 | 2026-07-03 | `3ace8ca` | Guard сравнивал только `destination == root`. Добавлены проверки `is_relative_to` в обе стороны: destination внутри source root (включая `.git`) и source внутри destination блокируются; regression test покрывает оба вложенных пути. |
| 41 | План компрессии закоммичен с template-плейсхолдером даты, `validate-project` падает | 2026-07-06 | 2026-07-06 | (в этой ветке) | При описании плейсхолдера прозой в план попал сырой литерал `<`+`YYYY-MM-DD`+`>`; правка порогов `4c83ab9` закоммичена без прогона валидатора, и `placeholder.remaining` дошёл до `main`. Формулировки переписаны без сырого литерала; урок — прогонять `validate-project --report-only` перед commit docs и не писать template-плейсхолдеры прозой. |
| 42 | Сплит CHANGELOG в компрессии оставлял архив без обратной ссылки | 2026-07-06 | 2026-07-06 | (в этой ветке) | `split_changelog` создавал `CHANGELOG_ARCHIVE.md` со ссылкой `[[CHANGELOG]]`, но не оставлял обратную ссылку в `CHANGELOG.md` — архив был связан в одну сторону (риск orphan/дрейфа навигации), в отличие от паттерна DEFECTS. Найдено dogfood-применением на самом репозитории. Добавлен `CHANGELOG_ARCHIVE_POINTER` (идемпотентная вставка в преамбулу) и регрессионный тест `test_pointer_is_idempotent`; архив внесён в [[INDEX]]. |

## Won't Fix

| # | Title | Discovered | Reason |
|---|---|---|---|
| 4 | POSIX symlink-тесты падают в Git Bash без symlink support | 2026-06-28 | Git Bash `ln -s` на этой Windows копирует файл, поэтому resolver-тесты получают неверный каталог. Windows поддерживается PowerShell-набором; POSIX symlink-сценарии выполняются в macOS/Linux и CI. |
| 33 | PowerShell bootstrap-тест падает локально на macOS в mock-git секции | 2026-07-02 | Дефект тестовой обвязки, а не продукта: pwsh на macOS кеширует резолв `git` в удалённый `mock-bin` путь из временного PATH (command caching). CI (Windows PowerShell 5.1 / pwsh 7 на windows-latest) сценарий не воспроизводит и полностью покрывает; профильные проверки скрипта проходят. Решение 2026-07-03: не чинить. |
