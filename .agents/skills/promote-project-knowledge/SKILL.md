---
name: promote-project-knowledge
description: Maintainer-only. Затвердевает уже принятую, вызревшую практику соседней базы Best Practices в обязательное правило стандарта new-project-rules через apply-promotion-candidate. Не для рядовых пользователей — они делятся опытом только кандидатами в Best Practices.
---

# Затвердевание практики Best Practices в правило NPR

Двухъярусная модель
([[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture|ADR-0003]]):
пользователи отдают опыт только в Best Practices (кандидатом через PR); стандарт
`new-project-rules` для пользователя read-only и меняется только рукой
администратора. Этот skill — **maintainer-only** редкий акт: взять уже принятую,
вызревшую практику Best Practices и сделать её обязательным правилом NPR.

Это не сбор уроков из проектов (его в NPR больше нет) и не изменение стандарта
пользователем. Обычный путь пользователя — `harvest-practice-candidates` в базе
Best Practices, а не этот skill.

## Когда применять

Только если верно всё:

- практика уже `accepted` в `Best Practices/practices/<раздел>/` (прошла review);
- она универсальна настолько, что должна выполняться во всех проектах по
  умолчанию, а не оставаться советом;
- вы действуете как администратор стандарта.

Если практика полезна, но не обязательна — оставить её в Best Practices, не
затвердевать.

## Подготовить источник

1. Найти корень `new-project-rules`, прочитать `AGENTS.md` и
   `docs/guides/AI_KNOWLEDGE_PORTABILITY.md`.
2. Найти исходную практику в соседней базе `Best Practices` (`accepted`, с
   provenance и evidence).
3. Проверить candidate files в `docs/quality/promotion-candidates/`: возможно,
   затвердевание уже оформлено кандидатом.

## Принять решение

1. Подтвердить, что правило должно быть обязательным (императив), а не советом.
2. Отделить «как делать хорошо» (остаётся знанием в Best Practices) от «обязан
   делать» (идёт в NPR правилом). Для сквозной темы: императив — в NPR,
   обоснование остаётся в Best Practices, без копирования rationale.
3. Удалить секреты, приватные идентификаторы и machine-specific paths.
4. Если обязательность сомнительна — показать решение пользователю и не менять
   стандарт молча.

## Оформить и применить

1. Оформить затвердевание кандидатом `PC-...` в
   `docs/quality/promotion-candidates/` со статусом `approved`, заполненными
   `Artifact Type` и `Proposed Target` и ссылкой на исходную практику Best
   Practices.
2. Запустить `apply-promotion-candidate` — он превратит кандидата в конкретное
   checked-in изменение стандарта (rule, template, test, validator, script,
   guide или skill).

## Отчёт

1. Назвать исходную практику Best Practices и итоговое правило NPR.
2. Указать, применялся ли `apply-promotion-candidate` и с каким результатом.
