---
type: guide
status: active
owner: project
last_verified: 2026-07-08
source_of_truth: repository
related:
  - "[[docs/guides/user-guide/workflows/README|Каталог workflow]]"
  - "[[docs/guides/user-guide/workflows/best-practices-user|Best Practices — workflow пользователя]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY|Перенос знаний между проектами]]"
  - "[[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture|ADR-0003]]"
  - "[[docs/architecture/BEST_PRACTICES_CONTRACT|Compatibility contract NPR ↔ Best Practices]]"
---

# Работа с практиками — полный процесс

Как опыт становится практикой, а практика — правилом. Все исполнители.
Визуальная версия: [best-practices-full.html](assets/best-practices-full.html).

Двухъярусная модель ([[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture|ADR-0003]]):
`Best Practices` — единственный обратный поток опыта; `new-project-rules` — стандарт,
для пользователя read-only. Пользователь отдаёт опыт кандидатом; администратор
принимает практику и в редких случаях затвердевает её в правило — это единая
роль ведения базы и стандарта (прежде различались «мейнтейнер» и «администратор»).

Каждый шаг: **исполнитель**, **запуск** (тип + триггер), **вход → результат**,
**сигнал** (как человек понимает, что настал его ход — на связке = выход
предыдущего шага; «внешн.» = сигнал извне потока).

## Оглавление

1. [[#Поток A — находка → практика в Best Practices|Поток A — находка → практика в Best Practices]]
2. [[#Поток B — затвердевание практики → правило стандарта (maintainer-only)|Поток B — затвердевание практики → правило стандарта]]
3. [[#Контур C — целостность между репозиториями|Контур C — целостность между репозиториями]]

## Поток A — находка → практика в Best Practices

| Шаг | Действие | Исполнитель | Запуск | Вход → Результат | Сигнал |
|---|---|---|---|---|---|
| A1 | Зафиксировать факт | агент·по правилу / пользователь→агент | `auto` (агент сам пишет дефект по правилу AGENTS.md) **или** `skill` — *«Зафиксируй урок»* · `/reflect-and-record` | Сбой/приём из работы → `DEFECTS.md` / `PLAYBOOK.md` (≥2 раз) / ADR | внешн.: обнаружен дефект в ходе работы |
| A2 | Собрать кандидатов | пользователь→агент | `skill` — *«Собери кандидатов в Best Practices из соседних проектов»* · `/harvest-practice-candidates` | Checked-in артефакты соседних проектов → harvest-preview shortlist | внешн.: решение поделиться опытом |
| A3 | Оформить файл-кандидат | пользователь→агент | `script` — `python3 scripts/new_candidate.py …` | Урок + провенанс (`source`, `added_by`) → `candidates/PC-*.md` (new/triaged, E0/E1) | harvest-preview одобрен |
| A4 | Локальная проверка | пользователь→агент | `script` — `make check` (unittest + validate.py + freshness) | Файл кандидата → зелёный validator | файл кандидата создан |
| A5 | Отправить на GitHub | пользователь→агент | `git` — *«Запушь ветку и открой PR»* · `git push` + `gh pr create` (агент спрашивает перед PR) | Ветка `candidate/*` + обоснование агента в описание PR → открытый PR в защищённый `main` | `make check` зелёный, кандидат готов |
| A6 | Автопроверка PR | система·CI | `auto` — `validate.yml` при открытии PR | Diff PR → статус-чек `validate` (красный блокирует merge) | PR открыт (событие GitHub) |
| A7 | Решение accept/reject | администратор | `skill` — *«Разбери кандидатов и прими решение»* · `/review-practice-candidates` | Кандидат + `practices/**` → вердикт | CI зелёный, PR готов к ревью |
| A8a | Accept | администратор | (тот же skill) | → `practices/<раздел>/PC-*.md` (E1=trial, E2/E3=accepted); кандидат→`accepted`+commit; PR влит | вердикт A7 |
| A8b | Reject | администратор | (тот же skill) | → кандидат→`rejected`+причина (журнал сохраняется) | вердикт A7 |
| A9 | Доставить в проекты | пользователь→агент | `skill` — *«Подтяни практики под стек»* · `/apply-best-practices` | `practices/**` + стек → common применён; решения в `.best-practices.json` | внешн.: правило-напоминание при определении стека |

**Защита `main` (условие A5–A8):** require PR + review approval + review from Code
Owners (`.github/CODEOWNERS`) + status check `validate` + block force push.
Настраивается владельцем один раз в GitHub Settings → Branches.

## Поток B — затвердевание практики → правило стандарта (maintainer-only)

| Шаг | Действие | Исполнитель | Запуск | Вход → Результат | Сигнал |
|---|---|---|---|---|---|
| B0 | Условие входа | администратор | `manual` — проверка критериев обязательности | Accepted-практика + вывод «обязательна всем» → решение начинать | внешн.: практика вызрела до обязательной |
| B1 | Gate контракта | администратор | `script` — `python3 scripts/check_best_practices_contract.py --best-practices-root "../Best Practices"` | `config/best-practices-contract.json` + BP → OK по remote/commit/hashes/status/routes/ADR, иначе стоп | решение о затвердевании принято |
| B2 | Оформить promotion-кандидат | администратор | `skill` — `/promote-project-knowledge` → `promotion_candidates.py create` | Accepted-практика, practice path, `source_commit` → `docs/quality/promotion-candidates/PC-*.md` (approved) | контракт-гейт зелёный |
| B3 | Материализовать в стандарт | администратор | `skill` — `/apply-promotion-candidate` | Один `approved` кандидат → артефакт NPR (rule/template/test/validator/script/skill/guide) | кандидат approved |
| B4 | Синхронизировать репозиторий | администратор | `manual` (тот же skill) | Изменение из B3 → обновлены README, INDEX, docs/README, CHANGELOG, шаблоны/тесты/скилы | изменение внесено |
| B5 | Traceability + отправка | администратор | `git` — `git push origin/main` (стандарт NPR не требует PR; агент спрашивает перед PR) | Изменение + checks → кандидат→`implemented`+commit; outcome в `.best-practices.json` | синхронизация завершена |

**Правило SSOT (B3):** императив живёт в NPR (`AGENTS.md`, самодостаточно),
обоснование остаётся в Best Practices — rationale не копируется.

## Контур C — целостность между репозиториями

| Шаг | Действие | Исполнитель | Запуск | Вход → Результат | Сигнал |
|---|---|---|---|---|---|
| C1 | Контрактный тест + Cross-repo E2E | система·CI | `auto` — `ci.yml` → contract + E2E (Ubuntu/Windows/macOS) | Contract.json + хеши; полная BP validation, реальный schema-2 report и outcomes → pass/fail | любой push/PR в NPR |
| C3 | Ежедневный live-сторож | система·CI | `auto` — `bp-pin-watch.yml` → pin check + checkout BP `main` + validation/report (cron `17 5 * * *`) | Reviewed pin и live repository → красный read-only сигнал при drift/invalid state; ничего не записывает | внешн.: расписание cron |
| C4 | Обновление pin | администратор | `git` — вручную, отдельный reviewable PR (5 шагов из контракт-доки) | Новый BP `main`, accepted-практика с evidence → обновлены commit/hashes/route/ADR | красный сигнал bp-pin-watch |

## Две решающие точки

- **A7** — пустить ли опыт в базу практик (администратор, accept/reject).
- **B0/B2** — сделать ли практику обязательным правилом (администратор), только
  после зелёного контракт-гейта B1.

Обе точки — одна роль администратора (ведёт базу и стандарт); различается режим,
а не лицо. Детально — [[docs/guides/user-guide/workflows/best-practices-admin|workflow администратора]].
