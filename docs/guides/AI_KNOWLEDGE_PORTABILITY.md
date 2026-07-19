---
type: guide
status: active
owner: project
last_verified: 2026-07-07
source_of_truth: repository
related:
  - "[[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture|ADR-0003]]"
  - "[[AGENTS]]"
  - "[[GLOBAL_AGENT_INSTRUCTIONS]]"
  - "[[docs/quality/DEFECTS]]"
  - "[[docs/quality/PLAYBOOK]]"
  - "[[docs/quality/PROMOTION_CANDIDATES]]"
  - "[[.agents/skills/promote-project-knowledge/SKILL|promote-project-knowledge]]"
  - "[[.agents/skills/apply-promotion-candidate/SKILL|apply-promotion-candidate]]"
---

# Перенос знаний между проектами

Знание движется по двухъярусной модели
([[docs/architecture/decisions/ADR-0003-two-tier-knowledge-architecture|ADR-0003]]):

- **`new-project-rules` (NPR) — конституция.** Малое ядро обязательных правил;
  для пользователя **read-only**, меняется только рукой администратора.
- **`Best Practices` — единственный обратный поток.** Весь опыт пользователей
  стекается только сюда, через кандидатов и review.

Проекты не сливают знания автоматически. Сырые Memory Codex и Claude остаются
локальным рабочим состоянием и не коммитятся — это совпадает с позицией вендоров:
Codex memories хранятся локально, не синхронизируются между машинами и не
являются source of truth
([Codex memories](https://developers.openai.com/codex/memories)).

## Слои знания

| Слой | Примеры | Источник истины | Куда движется |
|---|---|---|---|
| Контекст сессии | гипотезы, промежуточные выводы | текущий диалог | никуда |
| Локальная memory | наблюдения и предпочтения агента | Codex/Claude на этой машине | не коммитится |
| Знание проекта | ADR, дефекты, исследования, runbook | репозиторий проекта | остаётся в проекте |
| Общий опыт | практики «как делать хорошо» (по стеку/инструменту) | `Best Practices` | пользователь → кандидатом через PR |
| Стандарт | правила, шаблоны, тесты, scripts, skills | `new-project-rules` | администратор → сверху вниз |

## Две роли

- **Пользователь** отдаёт опыт **только в Best Practices**: находку по 1С, вебу,
  инструменту или промпту оформляет кандидатом и открывает Pull Request. Стандарт
  NPR он не меняет; баг инструмента NPR — обычным issue/PR.
- **Администратор** ведёт и версионирует стандарт NPR, ревьюит кандидатов Best
  Practices (accept/reject) и, в редких случаях, **затвердевает** вызревшую
  практику Best Practices в обязательное правило NPR.

Solo-владелец носит обе шляпы; роли различают режим, а не обязательно разных
людей.

## Путь пользователя: находка → Best Practices

1. Записать исходный факт в правильный артефакт проекта: `DEFECTS`, ADR,
   investigation, runbook или postmortem.
2. Если приём **сработал повторно** (≥2 раз) либо рабочее решение найдено после
   перебора нескольких неудачных вариантов — автоматически вынести его в
   [[docs/quality/PLAYBOOK]] как known-good pattern; во втором случае — сразу
   после проверки результата.
3. Если приём полезен не только этому проекту — оформить **кандидата в Best
   Practices** (`harvest-practice-candidates` в соседней базе), с provenance и
   без секретов, и открыть Pull Request. `main` базы под branch protection —
   принимает только review.
4. После accept практика попадает в `Best Practices/practices/<раздел>/` и
   доставляется в проекты через `apply-best-practices`.

Предпочитайте исполняемые формы (skill, сниппет, проверку) текстовому описанию.
OpenAI пометила локальные custom prompts (`~/.codex/prompts`) deprecated в пользу
skills ([Codex custom prompts](https://developers.openai.com/codex/custom-prompts)).
Качество поля `description` в SKILL.md критично: при нехватке контекста Codex
сокращает описания skills первыми — ключевые триггеры выносите в начало.

## Путь администратора: затвердевание Best Practices → правило NPR

Редкий maintainer-only акт, когда практика настолько универсальна, что должна
выполняться во всех проектах по умолчанию, а не оставаться советом.

1. [[.agents/skills/promote-project-knowledge/SKILL|`promote-project-knowledge`]]
   берёт `accepted`-практику Best Practices и оформляет затвердевание кандидатом
   `PC-...` в [[docs/quality/promotion-candidates/README|`promotion-candidates/`]].
2. [[.agents/skills/apply-promotion-candidate/SKILL|`apply-promotion-candidate`]]
   превращает один `approved` кандидат в конкретное checked-in изменение
   стандарта: rule, template, test, validator, script, guide или skill.

Для сквозной темы (например, «no secrets») действует правило SSOT: **императив**
живёт в NPR (`AGENTS.md`, самодостаточно), а **обоснование/доказательства** — в
Best Practices; rationale не копируется, связывается мягкой ссылкой.

## Как связаны DEFECTS, PLAYBOOK и обмен опытом

- Сбой, ошибка или регрессия сначала фиксируются в
  [[docs/quality/DEFECTS]].
- Подтверждённый минимум дважды удачный приём либо проверенное решение,
  найденное после перебора нескольких неудачных вариантов, автоматически
  выносится в [[docs/quality/PLAYBOOK]].
- Если приём полезен нескольким проектам — он идёт кандидатом **в Best
  Practices** (а не в стандарт напрямую).

## Backlog кандидатов (сторона NPR)

Затвердевания ведутся по модели «один кандидат — один файл» в
[[docs/quality/promotion-candidates/README|`promotion-candidates/`]];
[[docs/quality/PROMOTION_CANDIDATES]] — стабильная точка входа. Вход в этот
backlog — практика Best Practices, выбранная администратором на затвердевание,
а не скан проектов. ID создаёт генератор в формате `PC-YYYY-<12 hex>`; кандидат
указывает не только урок, но и форму реализации (`rule`, `template`, `test`,
`validator`, `script`, `skill`, `guide`).

## Примеры

- Ошибка конкретного API остаётся в `DEFECTS.md` этого проекта.
- Решение о выборе базы данных остаётся ADR исходного проекта.
- Повторяемый приём по вебу или 1С идёт кандидатом в Best Practices.
- Практика Best Practices, ставшая обязательной для всех проектов, затвердевается
  администратором в правило NPR.
- Сырое содержимое `~/.codex/memories/` или Claude auto memory не переносится.
