---
name: apply-promotion-candidate
description: Берёт один approved promotion candidate и переносит его в конкретные артефакты new-project-rules: rules, templates, tests, validators, scripts, guides или skills.
---

# Применение кандидата на promotion

Задача этого skill: взять одну уже разобранную карточку из
`docs/quality/PROMOTION_CANDIDATES.md` и превратить её в проверяемое изменение
репозитория `new-project-rules`.

## Найти источник правил

1. Найти корень `new-project-rules`: каталог должен содержать `AGENTS.md`,
   `docs/guides/AI_KNOWLEDGE_PORTABILITY.md`,
   `docs/quality/PROMOTION_CANDIDATES.md` и соответствующие шаблоны/skills.
2. Полностью прочитать корневой `AGENTS.md`,
   `docs/guides/AI_KNOWLEDGE_PORTABILITY.md` и
   `docs/quality/PROMOTION_CANDIDATES.md`. Они имеют приоритет над этим
   workflow.

## Выбрать кандидата

1. Работать с одним кандидатом за раз по его `ID`.
2. Требовать статус `approved`, если пользователь прямо не сказал применить
   конкретную запись немедленно.
3. Проверить, что для кандидата заполнены:
   - `Generalized Lesson`;
   - `Evidence`;
   - `Artifact Type`;
   - `Proposed Target`.
4. Если урок всё ещё выглядит частным или target выбран плохо, остановиться и
   вернуть запись в `triaged` с пояснением в `Notes`.

## Преобразовать кандидат в change set

1. Переносить не сам текст кандидата, а его нормализованное воплощение.
2. Выбирать форму реализации по `Artifact Type`:
   - `rule` — обновить правила, обычно `templates/new-project/AGENTS.template.md`
     и связанные rule sources;
   - `template` — обновить или добавить файл в `templates/new-project/`;
   - `test` или `validator` — добавить проверку, которая удерживает новый
     инвариант автоматически;
   - `script` — добавить reusable automation, если текстового правила
     недостаточно;
   - `skill` — оформить workflow в `.agents/skills/` и тонкий bridge в
     `.claude/skills/`; ключевые триггеры — в начало `description`
     (Codex сокращает описания skills первыми); не создавать deprecated
     `~/.codex/prompts`;
   - `guide` — обновить `docs/guides/`, если изменение требует
     user-facing process documentation.
3. Предпочитать исполняемую форму вместо чисто текстового описания, если это
   практически возможно.

## Синхронизировать репозиторий

1. Обновить все связанные источники в одной задаче:
   - `README.md`;
   - `INDEX.md`;
   - `docs/README.md`;
   - `CHANGELOG.md`;
   - нужные templates, guides, scripts, tests и skills.
2. Если кандидат затрагивает общий rule layer, проверить, не нужно ли также
   обновить `GLOBAL_AGENT_INSTRUCTIONS.md` и активный baseline по действующим
   правилам проекта.
3. Сохранить traceability: в `PROMOTION_CANDIDATES.md` обновить статус на
   `implemented`, записать commit reference и итоговый target.

## Проверить результат

1. Запустить относящиеся проверки: syntax checks, regression tests и skill
   checks для затронутых артефактов.
2. Проверить отсутствие секретов, placeholders, raw memory и абсолютных
   machine-specific paths.
3. Убедиться, что новый механизм действительно применяет lesson, а не просто
   описывает его словами.

## Отчёт

1. Сообщить:
   - какой `ID` реализован;
   - из какого источника пришёл урок;
   - во что именно он превращён в `new-project-rules`;
   - какие проверки пройдены.
2. Если кандидат не удалось применить корректно, вернуть его в `triaged` или
   `rejected` с явной причиной.
