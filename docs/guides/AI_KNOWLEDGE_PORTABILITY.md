---
type: guide
status: active
owner: project
last_verified: 2026-07-06
source_of_truth: repository
related:
  - "[[AGENTS]]"
  - "[[GLOBAL_AGENT_INSTRUCTIONS]]"
  - "[[docs/quality/DEFECTS]]"
  - "[[docs/quality/PLAYBOOK]]"
  - "[[docs/quality/PROMOTION_CANDIDATES]]"
  - "[[.agents/skills/promote-project-knowledge/SKILL|promote-project-knowledge]]"
  - "[[.agents/skills/harvest-project-lessons/SKILL|harvest-project-lessons]]"
  - "[[.agents/skills/apply-promotion-candidate/SKILL|apply-promotion-candidate]]"
---

# Перенос знаний между проектами

Проекты не сливают свои знания в общий репозиторий автоматически.
`new-project-rules` хранит только проверенные и обобщённые практики, полезные
для нескольких будущих проектов. Сырые Memory Codex и Claude остаются
локальным рабочим состоянием и не коммитятся.

Это совпадает с официальной позицией вендоров: OpenAI указывает, что Codex
memories и sessions хранятся локально, не синхронизируются между машинами и не
являются source of truth — обязательные правила должны жить в `AGENTS.md` и
checked-in документации
([Codex memories](https://developers.openai.com/codex/memories)).

## Четыре слоя знания

| Слой | Примеры | Источник истины | Перенос |
|---|---|---|---|
| Контекст сессии | гипотезы, промежуточные выводы | текущий диалог | не переносится |
| Локальная memory | наблюдения и предпочтения агента | Codex или Claude на этом компьютере | не коммитится |
| Знание проекта | ADR, дефекты, исследования, runbook | репозиторий исходного проекта | остаётся в проекте |
| Общий стандарт | правила, шаблоны, тесты, scripts, skills | `new-project-rules` | синхронизируется через Git |

## Критерии promotion

Знание можно переносить в общий стандарт, только если оно:

1. вероятно повторится как минимум в двух независимых проектах;
2. формулируется без частного кода, бизнеса и инфраструктуры источника;
3. подтверждено дефектом, исследованием, тестом или воспроизводимым опытом;
4. улучшает bootstrap, безопасность, документацию или работу агентов;
5. превращается в правило, шаблон, тест, validator, script или skill;
6. очищено от секретов, персональных данных, приватных идентификаторов и
   абсолютных путей конкретного компьютера.

Если критерии не выполнены или применимость неясна, знание остаётся в исходном
проекте. Агент может предложить promotion, но не должен молча менять общий
стандарт.

Среди исполняемых форматов переноса предпочитайте **skill**: он коммитится,
шарится через репозиторий и распознаётся обоими агентами. OpenAI пометила
локальные custom prompts (`~/.codex/prompts`) deprecated в пользу skills
([Codex custom prompts](https://developers.openai.com/codex/custom-prompts)),
поэтому новые переносимые workflow оформляйте как skill в `.agents/skills/` с
тонким мостом в `.claude/skills/`, а не как локальные prompts.

Качество поля `description` в SKILL.md критично для имплицитного вызова: при
нехватке контекста Codex сокращает описания skills первыми, и триггеры в конце
описания теряются. Ключевые триггеры и типовые фразы пользователя выносите в
начало `description`.

## Процесс

1. Записать исходный факт в правильный артефакт проекта: defect, ADR,
   investigation, runbook или postmortem.
2. Отделить наблюдаемый факт от предполагаемого общего урока.
3. Проверить критерии promotion и найти независимое подтверждение, когда это
   разумно.
4. Перед прямым переносом решить, какая ветка workflow нужна:
   оставить lesson в исходном проекте, сначала собрать candidate или уже
   применить approved candidate.
5. Составить карточку promotion и получить согласие пользователя, если перенос
   не был явно запрошен.
6. Реализовать обобщённое изменение в `new-project-rules` вместе с тестом или
   другой проверкой.
7. Обновить все связанные источники правил, шаблоны, skills, индексы и журнал
   изменений в одной задаче.
8. Сохранить ссылку на исходный артефакт, не копируя его приватное содержание.

## Operational workflow

Для регулярного обогащения общего стандарта используйте двухшаговый pipeline:

1. [[.agents/skills/harvest-project-lessons/SKILL|`harvest-project-lessons`]]
   просматривает соседние git-проекты, извлекает кандидатов из `DEFECTS`,
   `PLAYBOOK`, ADR, research и runbook, а затем нормализует их в
   отдельными файлами в
   [[docs/quality/promotion-candidates/README|`promotion-candidates/`]].
2. Review переводит запись в `approved` или `rejected`.
3. [[.agents/skills/apply-promotion-candidate/SKILL|`apply-promotion-candidate`]]
   берёт один `approved` кандидат и превращает его в конкретные checked-in
   артефакты `new-project-rules`.

Так общий стандарт получает не сырые project lessons, а уже очищенные и
разобранные кандидаты с понятным target.

`promote-project-knowledge` в этой схеме работает как orchestration entrypoint:
он не обязан сам менять репозиторий, а сначала определяет, нужна ли ветка
`harvest` или `apply`.

## Как связаны DEFECTS, PLAYBOOK и promotion

- Сбой, ошибка, регрессия или неверное решение сначала фиксируются в
  `docs/quality/DEFECTS.md`.
- Если способ исправления или рабочий приём подтвердился минимум дважды и стал
  повторяемым, его можно вынести в `docs/quality/PLAYBOOK.md` как known-good
  pattern.
- Если этот паттерн полезен не только одному проекту, а нескольким независимым
  проектам, его уже стоит предлагать к promotion в `new-project-rules`.

Иными словами: `DEFECTS` хранит негативные уроки и сбои, `PLAYBOOK` хранит
проверенные удачные способы действий, а promotion переносит только
кросс-проектный вывод.

## Карточка promotion

```text
Источник: <project/artifact/reference>
Наблюдение: <проверенный факт>
Обобщённый урок: <независимая от проекта формулировка>
Область применения: <каким проектам полезно>
Подтверждение: <defect/test/research/reproduction>
Предлагаемый артефакт: <rule/template/test/validator/script/skill>
Очищено от секретов и локальных деталей: да/нет
Проверено: YYYY-MM-DD
```

## Backlog кандидатов

Рабочая очередь ведётся по модели «один кандидат — один файл» в
[[docs/quality/promotion-candidates/README|`promotion-candidates/`]], а
[[docs/quality/PROMOTION_CANDIDATES]] остаётся стабильной точкой входа. Это не журнал
дефектов и не playbook, а staging-area между project lessons и checked-in
standard artifacts.

Минимальная status model:

- `new` — найден, но ещё не разобран;
- `triaged` — lesson очищен и связан с target;
- `approved` — разрешено переносить;
- `implemented` — перенос выполнен и связан с commit;
- `rejected` — перенос отклонён.

Новый ID создаётся генератором и имеет collision-resistant формат
`PC-YYYY-<12 lowercase hex>`; legacy ID не переименовываются. Кандидат должен
указывать не только lesson, но и **форму реализации**:
`rule`, `template`, `test`, `validator`, `script`, `skill` или `guide`.
Именно эта привязка позволяет второму workflow переносить урок как change set,
а не как абстрактную заметку.

## Примеры

- Ошибка конкретного API остаётся в `docs/quality/DEFECTS.md` этого API.
- Решение о выборе базы данных остаётся ADR исходного проекта.
- Повторяемая проблема чтения UTF-8 в PowerShell становится общим правилом и
  regression test в `new-project-rules`.
- Сырое содержимое `~/.codex/memories/` или Claude auto memory не переносится;
  переносится только проверенный и очищенный вывод.
