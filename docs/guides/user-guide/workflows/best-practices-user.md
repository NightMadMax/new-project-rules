---
type: guide
status: active
owner: project
last_verified: 2026-07-08
source_of_truth: repository
related:
  - "[[docs/guides/user-guide/workflows/README|Каталог workflow]]"
  - "[[docs/guides/user-guide/workflows/best-practices-full|Best Practices — полный процесс]]"
  - "[[docs/guides/user-guide/workflows/best-practices-admin|Best Practices — workflow администратора]]"
  - "[[docs/guides/AI_KNOWLEDGE_PORTABILITY|Перенос знаний между проектами]]"
---

# Работа с практиками — workflow пользователя

Только твои действия, с явным **«Где»** — в какой папке открыть агента. Что
сделать, чтобы урок из проекта стал принятой практикой базы и вернулся во все твои
проекты. Визуальная версия:
[best-practices-user.html](assets/best-practices-user.html).

**Цель:** твой повторяемый приём становится `accepted`-практикой в общей базе и
доставляется в проекты через `apply-best-practices`.

Автоматика (CI) и ревью администратора показаны как ожидание — это **не твои шаги**.

## Ты работаешь в двух местах

- 📁 **твой проект** — здесь фиксируешь урок и применяешь готовые практики.
- 📁 **`Best Practices`** — здесь собираешь кандидатов и открываешь Pull Request
  (skill `/harvest-practice-candidates`).

## Шаги

1. **Зафиксировать урок в проекте.** — 📁 **твой проект**
   - Дефект агент часто пишет и сам (правило `AGENTS.md`); либо явно:
     *«Зафиксируй этот урок, занеси в дефекты»* · `/reflect-and-record`.
   - Готово, когда урок в `DEFECTS.md` / `PLAYBOOK.md` (приём, сработавший ≥2
     раз, либо проверенное решение после нескольких неудачных вариантов).

2. **Запустить сбор кандидатов.** — 📁 **`Best Practices`**
   - Открыть агента (Claude Code / Codex) в папке `Best Practices`; написать
     *«Собери кандидатов в Best Practices из соседних проектов»* ·
     `/harvest-practice-candidates`.
   - Получишь harvest-preview: shortlist уроков + что отброшено и почему.

3. **Просмотреть и одобрить preview.** — 📁 **`Best Practices`** (тот же агент)
   - Проверить shortlist, при желании сузить область. После одобрения агент сам
     создаст `candidates/PC-*.md` и прогонит `make check`.
   - Готово, когда файл кандидата создан, `make check` зелёный.

4. **Отправить на GitHub (открыть PR).** — 📁 **`Best Practices`** (тот же агент)
   - Написать *«Запушь ветку и открой PR»*. Агент выполнит `git push` +
     `gh pr create` и **спросит подтверждение перед созданием PR**. Один PR —
     один кандидат.
   - Получишь открытый Pull Request; обоснование агента уходит в описание PR.

   > ⚙ **Само:** GitHub Actions `validate.yml` проверяет PR; красный чек
   > блокирует merge — тогда исправить и запушить снова.
   >
   > ⏳ **Ожидание:** администратор разбирает кандидата
   > (`/review-practice-candidates`): **accept** → практика попадает в
   > `practices/**`, PR влит; **reject** → причина в кандидате. Целевой ответ —
   > 7 дней.

5. **Подтянуть практику в свои проекты.** — 📁 **твой проект**
   - Открыть агента в папке своего проекта; написать *«Подтяни практики Best
     Practices под стек»* · `/apply-best-practices`. Напоминание сработает само
     при определении стека проекта.
   - Результат: практика применена; выбор зафиксирован в `.best-practices.json`.

## Граница зоны пользователя

Твоя зона — только `Best Practices`: ты предлагаешь опыт кандидатом. Решение
accept/reject и тем более превращение практики в обязательное правило стандарта —
не твои шаги (роль администратора, см.
[[docs/guides/user-guide/workflows/best-practices-admin|workflow администратора]]
и [[docs/guides/user-guide/workflows/best-practices-full|полный процесс]]).
