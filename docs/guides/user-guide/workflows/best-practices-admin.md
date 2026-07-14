---
type: guide
status: active
owner: project
last_verified: 2026-07-08
source_of_truth: repository
related:
  - "[[docs/guides/user-guide/workflows/README|Каталог workflow]]"
  - "[[docs/guides/user-guide/workflows/best-practices-full|Best Practices — полный процесс]]"
  - "[[docs/guides/user-guide/workflows/best-practices-user|Best Practices — workflow пользователя]]"
  - "[[docs/architecture/BEST_PRACTICES_CONTRACT|Compatibility contract NPR ↔ Best Practices]]"
---

# Одобрение и применение практик — workflow администратора

Только действия администратора, с явным **«Где»** — в какой папке-репозитории
открыть агента (Claude Code / Codex) и что там написать. Визуальная версия:
[best-practices-admin.html](assets/best-practices-admin.html).

**Одна роль, объединяющая две прежние.** Раньше различали «мейнтейнера» (приём
практик) и «администратора» (стандарт). Здесь это одна роль.

**Результат роли:** курируемая база практик + (редко) вызревшая практика
становится обязательным правилом стандарта.

## Ты работаешь в двух соседних папках-репозиториях

- 📁 **`Best Practices`** — приём практик. Здесь skill
  `/review-practice-candidates`.
- 📁 **`Правила для нового проекта`** (new-project-rules) — стандарт. Здесь
  `/promote-project-knowledge`, `/apply-promotion-candidate`, контракт-скрипт.

## Режим 1 — разбор входящих кандидатов (регулярно)

**Где:** папка `Best Practices`.

1. **Разобрать кандидата и принять решение.**
   - Сигнал: пользователь открыл PR с кандидатом, CI `validate` зелёный.
   - Открыть агента в папке `Best Practices`; написать *«Разбери кандидатов и
     прими решение»* (или `/review-practice-candidates`); пройти дедуп, качество,
     обобщённость, чистоту, evidence.
   - **accept** → практика в `practices/<раздел>/PC-*.md` (E1=trial,
     E2/E3=accepted), PR влит; **reject** → причина в кандидате (журнал).

## Режим 2 — затвердевание практики в правило стандарта (редко)

**Где:** папка `Правила для нового проекта`. Только когда практика вызрела до
обязательной для всех проектов.

2. **Проверить условие и контракт-гейт.**
   - Сигнал: практика `accepted` в BP вызрела до обязательной (собственное суждение).
   - Открыть агента в папке `Правила для нового проекта`; запустить
     `python3 scripts/check_best_practices_contract.py --best-practices-root "../Best Practices"`.
   - Готово, когда гейт зелёный (иначе сначала обновить pin — режим 3).

3. **Оформить promotion-кандидат.**
   - В том же агенте написать *«Затверди эту практику как правило стандарта»*
     (или `/promote-project-knowledge`); указать практику BP и `source_commit`.
   - → `docs/quality/promotion-candidates/PC-*.md`, status approved, задан
     `artifact_type` + `proposed_target`.

4. **Применить кандидата в стандарт.**
   - В том же агенте написать *«Примени этот кандидат»* (или
     `/apply-promotion-candidate`).
   - Skill превращает в rule / template / test / validator / script / skill /
     guide и синхронизирует README, INDEX, CHANGELOG.

5. **Зафиксировать traceability и отправить.**
   - В том же агенте написать *«Закоммить и запушь»* · `git push origin/main`
     (стандарт NPR не требует PR; агент спрашивает перед PR).
   - → Кандидат → `implemented` + commit; outcome в `.best-practices.json`.

## Режим 3 — поддержание целостности связки (по сигналу)

**Где:** папка `Правила для нового проекта`.

> ⚙ **Само:** CI (`ci.yml`, `bp-pin-watch.yml`) прогоняет контрактный тест,
> cross-repo E2E с полной validation и ежедневный live-сторож pin/report.
> Заходить никуда не надо.

6. **Обновить pin.**
   - Сигнал: красный сигнал `bp-pin-watch` (GitHub → Actions или письмо).
   - Открыть агента в папке `Правила для нового проекта`; обновить pin вручную
     отдельным reviewable PR — 5 шагов из
     [[docs/architecture/BEST_PRACTICES_CONTRACT|контракт-доки]]; не смешивать с
     реализацией правила.
   - → Обновлены commit / hashes / route / ADR expectations.

## Правило SSOT

При затвердевании императив живёт в NPR (`AGENTS.md`, самодостаточно),
обоснование остаётся в Best Practices — rationale не копируется.
