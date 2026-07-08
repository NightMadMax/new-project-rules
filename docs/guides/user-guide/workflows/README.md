---
type: guide-index
status: active
owner: project
last_verified: 2026-07-08
source_of_truth: repository
related:
  - "[[docs/guides/user-guide/README|Руководство пользователя (папка)]]"
  - "[[docs/guides/user-guide/workflows/best-practices-full|Best Practices — полный процесс]]"
  - "[[docs/guides/user-guide/workflows/best-practices-user|Best Practices — workflow пользователя]]"
---

# Каталог workflow

Пошаговые разборы процессов проекта. Каждый шаг кодирует шесть полей:
**действие**, **исполнитель** (агент·по правилу / пользователь→агент /
система·CI / администратор), **запуск** (auto / skill (фраза +
`/имя`) / script / manual / git), **вход**, **результат** и **сигнал** (как
человек понимает, что настал его ход).

Роли **мейнтейнера** и **администратора** объединены в одну — **администратор**
(ведёт базу практик *и* стандарт: и review кандидатов, и затвердевание в правила).

У каждого процесса — полный отчёт плюс отчёты по ролям (пользователь, администратор).

## Работа с практиками (Best Practices ↔ new-project-rules)

- [[docs/guides/user-guide/workflows/best-practices-full|Работа с практиками — полный процесс]]
  — опыт → практика → правило, все роли. ([HTML](assets/best-practices-full.html))
- [[docs/guides/user-guide/workflows/best-practices-user|Работа с практиками — workflow пользователя]]
  — только действия пользователя. ([HTML](assets/best-practices-user.html))
- [[docs/guides/user-guide/workflows/best-practices-admin|Одобрение и применение практик — workflow администратора]]
  — разбор кандидатов, затвердевание в правила, поддержание pin.
  ([HTML](assets/best-practices-admin.html))

## Настройка и проекты

- [[docs/guides/user-guide/workflows/setup-new-computer-user|Настройка нового компьютера — workflow пользователя]]
  — линейный процесс, два маршрута (🗣 агенту / ⌨ вручную).
  ([HTML](assets/setup-new-computer-user.html))
- [[docs/guides/user-guide/workflows/projects-user|Работа с проектами — карта действий пользователя]]
  — создание проекта как процесс + каталог остальных действий.
  ([HTML](assets/projects-user.html))

## Схема наименования

Заголовок отчёта = **`<действие> — <охват/роль>`**, чтобы из названия было видно,
что в отчёте делается. Примеры: «Работа с практиками — workflow пользователя»,
«Одобрение и применение практик — workflow администратора», «Настройка нового
компьютера — workflow пользователя», «Работа с проектами — карта действий
пользователя».

## Как добавить workflow по новому процессу

Проще всего — skill
[[.agents/skills/document-process-workflow/SKILL|document-process-workflow]]: он
создаёт и обновляет эти отчёты по модели ниже и синхронизирует индексы. Вручную:

1. Создать `<process>-full.md` и `<process>-user.md` по образцу Best Practices.
2. Заголовок каждой страницы дать по схеме наименования выше.
3. Положить визуальные HTML в `assets/` теми же basename.
4. Добавить страницы в этот индекс и в `related` соответствующих файлов.
5. Соблюдать [[docs/guides/user-guide/README|модель]]: полный процесс + отчёты по
   ролям, шесть полей на шаг + «Где», сигнал Д1/Д2.
