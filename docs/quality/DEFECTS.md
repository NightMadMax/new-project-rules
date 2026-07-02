---
type: defect-log
status: active
owner: project
last_verified: 2026-06-30
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
| 30 | `USE_THIS_PROJECT.md` неполон | 2026-07-02 | guides | Секция 8 «Перенести знания» даёт только Codex-вызовы без Claude Code эквивалентов; skill `reflect-and-record` не упомянут вовсе, остальные 7 workflows покрыты. |
| 31 | CHANGELOG `Unreleased` разросся и отстаёт | 2026-07-02 | changelog | ~105 строк накопили пять версий работы после `v1.9.0`; релиз не нарезан; новый гайд `USE_THIS_PROJECT.md` не отражён. |
| 32 | `TOOLS.md` не каталогизирует большинство скриптов | 2026-07-02 | tools catalog | 32 из 40 скриптов `scripts/` не упомянуты; нужен каталог либо явная ссылка на [[INDEX]]/[[docs/quality/TESTING|TESTING]] как источник. |

## Fixed

| # | Title | Discovered | Fixed | Commit | Root Cause |
|---|---|---|---|---|---|
| 1 | Mojibake в UI-метаданных skill | 2026-06-28 | 2026-06-28 | `a999788` | Native Windows исказил кириллические `--interface`; UI metadata переведены в ASCII. |
| 2 | Skill helpers требуют отсутствующий PyYAML | 2026-06-28 | 2026-06-28 | `a999788` | Runtime не содержал `PyYAML`; добавлен `requirements-dev.txt`, установлен и проверен `PyYAML 6.0.3`. |
| 3 | Skill helpers читают UTF-8 как cp1251 | 2026-06-28 | 2026-06-28 | `a999788` | `Path.read_text()` выбрал legacy code page; helpers запускаются с `PYTHONUTF8=1`, workaround записан в [[TOOLS]]. |
| 5 | Переносимые правила расходятся с активными | 2026-06-29 | 2026-06-29 | `8a669b6` | Атомарное обновление global/project/template rules не было проверено semantic contract test. |
| 6 | Skill-тесты не запускаются в CI | 2026-06-29 | 2026-06-29 | `8a669b6` | Workflow не вызывал существующие `test-skills.*`. |
| 11 | Архитектура заявляет четыре слоя и перечисляет пять | 2026-06-29 | 2026-06-29 | `8a669b6` | Число слоёв не обновили после добавления Agent Skills. |
| 12 | Defect template создаёт фиктивный открытый дефект | 2026-06-29 | 2026-06-29 | `8a669b6` | Пример был помещён в рабочую таблицу вместо инструкции под ней. |
| 7 | Расширенные профили создают неполный docs index | 2026-06-29 | 2026-06-29 | `114788c` | Bootstrap обновлял только корневой `INDEX.md`, но не профильные разделы `docs/README.md`. |
| 8 | Claude одновременно optional и required | 2026-06-29 | 2026-06-29 | `114788c` | Environment check не различал agent mode и всегда требовал оба CLI. |
| 9 | Scoped setup создаёт внешний каталог до проверки | 2026-06-29 | 2026-06-29 | `114788c` | Scope path окончательно проверялся только после `mkdir` / `New-Item`. |
| 10 | Bootstrap не откатывает частично созданный проект | 2026-06-29 | 2026-06-29 | `114788c` | Генерация выполнялась прямо в destination без failure cleanup. |
| 13 | Shell no-git fixture не предоставляет grep | 2026-06-29 | 2026-06-29 | `9a6b445` | После manifest-driven refactor bootstrap использует standard `grep` для index relationships, но изолированный PATH теста содержал старый неполный список команд. |
| 14 | Validator применяет document schema к Agent Skills | 2026-06-29 | 2026-06-29 | `1f60012` | Frontmatter validation не различала document schema `type/status` и Agent Skill schema `name/description`. |
| 15 | В корне rules project существует пустой nested vault | 2026-06-29 | 2026-06-29 | `1f60012` | Пустой локальный `.obsidian` не отслеживался Git и оставался невидимым прежним repository checks. |
| 16 | Shell wrapper выбирает нерабочий python3 App Alias | 2026-06-29 | 2026-06-29 | `1f60012` | Runtime выбирался по наличию команды, а не по успешному probe Python 3.9+. |
| 17 | PowerShell tests оставляют пустые Git identity env vars | 2026-06-29 | 2026-06-29 | `d760c69` | Restore отсутствующих variables через .NET оставлял пустые process values; теперь отсутствующие names удаляются через `Env:` provider и проверяются isolation regression test. |
| 18 | Validator падает на JSON metadata с non-object root | 2026-06-29 | 2026-06-29 | `d760c69` | После schema finding non-object JSON передавался дальше как metadata dict; теперь downstream получает `None`, а regression test проверяет finding без traceback. |
| 19 | create-new-project планирует metadata до clean-tree commit | 2026-06-30 | 2026-06-30 | `e4dcd52` | Workflow запускал plan до commit стартовых документов; теперь completed configuration коммитится до plan, а metadata — отдельным commit после apply. |
| 20 | Migration apply может заменить symlink обычным файлом | 2026-06-30 | 2026-06-30 | `e4dcd52` | Atomic replace не различал file и symlink; project/global plans теперь блокируют symlink destinations и требуют ручного решения ownership. |
| 21 | Верхнеуровневые документы дублируют per-command manual | 2026-06-30 | 2026-06-30 | `487a1b6` | Верхний уровень был перегружен повтором per-command manual вместо краткого overview и ссылок на `docs/guides/`, что создавало риск drift. |
| 22 | Guide по новому компьютеру не объясняет агентский workflow достаточно явно | 2026-06-30 | 2026-06-30 | `487a1b6` | В guide не хватало явных agent-first примеров запросов и ожидаемого поведения; сценарий был в основном ручным. |
| 23 | PLAYBOOK объявлен в правилах, но отсутствует в структуре и навигации проекта | 2026-06-30 | 2026-06-30 | `97ae46f` | Правила и skills уже требовали `docs/quality/PLAYBOOK.md`, но индекс, docs map и сам rules-project не отражали этот артефакт как часть рабочей модели. |
| 24 | Модель артефактов не описывает DEFECTS и PLAYBOOK как штатные knowledge artifacts | 2026-06-30 | 2026-06-30 | `97ae46f` | Исследовательская taxonomy отставала от operational rules и не фиксировала negative/positive learning loop в явном виде. |
| 25 | Defect-tracking contract расходится с форматом журнала DEFECTS | 2026-06-30 | 2026-06-30 | `97ae46f`, `fb079d3` | Правила описывали `status` как поле записи, тогда как шаблон и реальный журнал кодировали статус через секции `Open` / `Fixed` / `Won't Fix`. |
| 26 | PROJECT.md не отражает existing-project workflows как часть фактического scope | 2026-06-30 | 2026-06-30 | `97ae46f` | Верхнеуровневое описание проекта отставало от уже реализованных assessment/standardization сценариев. |
| 27 | Переносимые и шаблонные agent instructions отставали от обновлённого defect contract | 2026-06-30 | 2026-06-30 | `fb079d3` | После выравнивания repo-local правил portable copy и template сохраняли старую формулировку, что снова создавало риск drift в новых проектах. |
| 28 | Активный `~/.codex/AGENTS.md` разошёлся с переносимой копией, managed markers утрачены | 2026-07-02 | 2026-07-02 | см. [[ACTIONS]] | После adoption 2026-06-30 активный файл был перезаписан старой редакцией без markers (вероятно, старый `setup-global-agents` на другом компьютере; root cause подтвердить). Исправлено: user-reviewed копия portable → active, затем migration `0002` (fingerprint `18a73ff1…f063d`), postcondition `managed_match`. |
| 29 | `docs/README.md` не содержит два research-файла | 2026-07-02 | 2026-07-02 | `7fb88eb` | Секция «Исследования» не пополнялась при добавлении research-файлов; ссылки на AGENT_RUNTIME_CAPABILITIES_2026 и AGENT_COMMUNITY_PRACTICES_2026 добавлены. |

## Won't Fix

| # | Title | Discovered | Reason |
|---|---|---|---|
| 4 | POSIX symlink-тесты падают в Git Bash без symlink support | 2026-06-28 | Git Bash `ln -s` на этой Windows копирует файл, поэтому resolver-тесты получают неверный каталог. Windows поддерживается PowerShell-набором; POSIX symlink-сценарии выполняются в macOS/Linux и CI. |
