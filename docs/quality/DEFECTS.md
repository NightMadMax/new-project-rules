---
type: defect-log
status: active
owner: project
last_verified: 2026-07-02
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
| 33 | PowerShell bootstrap-тест падает локально на macOS в mock-git секции | 2026-07-02 | scripts/test-bootstrap.ps1 | Секции mock add/commit и «git status failure detection» падают: pwsh резолвит `git` в уже удалённый `mock-bin` путь из временного PATH (command caching). Воспроизводится на чистом HEAD, профильные проверки проходят; CI (Windows PowerShell 5.1 / pwsh 7) не затронут. |

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

## Won't Fix

| # | Title | Discovered | Reason |
|---|---|---|---|
| 4 | POSIX symlink-тесты падают в Git Bash без symlink support | 2026-06-28 | Git Bash `ln -s` на этой Windows копирует файл, поэтому resolver-тесты получают неверный каталог. Windows поддерживается PowerShell-набором; POSIX symlink-сценарии выполняются в macOS/Linux и CI. |
