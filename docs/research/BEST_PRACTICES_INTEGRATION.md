---
type: research
status: active
owner: project
last_verified: 2026-07-06
source_of_truth: repository
related:
  - "[[docs/guides/CREATE_NEW_PROJECT]]"
  - "[[templates/new-project/AGENTS.template|AGENTS.template]]"
  - "[[CHANGELOG]]"
---

# Research: интеграция базы Best Practices в создание проекта

## Question

- Как подключить соседнюю базы знаний `Best Practices` к `create-new-project`
  так, чтобы новый проект автоматически получал применимые практики, не ломая
  переносимость проекта, pull-модель базы и единый source of truth?

## Hypotheses

- Достаточно вызывать существующий skill `apply-best-practices` из
  `create-new-project`.
- Провижининг (установку/обновление базы) можно держать в самом скилле базы.
- Напоминание «подтянуть стековые практики» можно оформить обычным правилом.

## Method and Evidence

- Прочитаны репозиторий `Best Practices` (README, PROJECT, CONTRIBUTING,
  `.project-standard.json`, skill `apply-best-practices`) и `create-new-project`.
- Проверено размещение скиллов: глобальных нет (`~/.claude/skills`,
  `~/.agents/skills` пусты); скиллы привязаны к репозиторию. `apply-best-practices`
  существует только в папке `Best Practices`; `create-new-project` не копирует
  скиллы в новый проект (`templates/new-project/` — только Markdown).
- Проверена защита `main` базы: активный repository ruleset «Protect main»
  (require PR + review + Code Owners + status check `validate`, block force push).

## Findings

- Гипотеза «просто вызвать skill» неверна: из свежего проекта
  `apply-best-practices` **не виден как команда** (скиллы per-project). Значит
  вызов возможен только чтением его SKILL.md как файла из базы-соседа.
- «Курица и яйцо»: логику установки базы нельзя держать только в скилле базы —
  пока база не склонирована, скилла нет. Провижининг обязан жить в
  `create-new-project` (он присутствует всегда).
- Провижининг делаем **самодостаточным** в new-project-rules и в сгенерированном
  `AGENTS.md`, поэтому репозиторий `Best Practices` в основной работе менять не
  нужно (кросс-репо правок, PR и вопроса branch protection в ядре нет).
- Стек нового проекта на старте неизвестен → применять при создании только
  `common`; стековые практики (`1c`, `web`) — позже, по правилу-напоминанию.
- Триггер «по определению стека» — вероятностный (не хук): страховка, не гарантия.

## Conclusion

Принятая архитектура (реализована, v1.15.0):

- `create-new-project` на финальном шаге предлагает (opt-in) обновить/установить
  базу соседом `../Best Practices` и применяет `common`.
- Шаблон `AGENTS.template.md` несёт компактное самодостаточное правило: при
  определении стека прочитать `apply-best-practices/SKILL.md` из базы и выполнить
  для стека; при отсутствии базы — предложить клонировать.
- Решения пользователя фиксируются в `.best-practices.json` (`optout`/`applied`),
  чтобы отклонённые/применённые разделы не предлагались повторно; файл коммитится.
- В `Best Practices` — только уточнение формулировки `apply-best-practices`
  (PR #1, merge `d8427628`).

Отдача вырастет по мере наполнения `practices/**`; сейчас разделы почти пустые —
хук поставлен на вырост.
