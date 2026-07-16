# Status model

## Scope

| Jira project | Issue types | Owner | Verified |
|---|---|---|---|
|  |  |  |  |

## Canonical groups

| Group | Jira statuses | Meaning |
|---|---|---|
| `backlog` |  | Работа не начата |
| `in_progress` |  | Работа выполняется |
| `review` |  | Результат проверяется |
| `blocked` |  | Нужна внешняя разблокировка |
| `done` |  | Работа завершена |
| `cancelled` |  | Работа прекращена |

## Rules

- Jira остаётся источником истины; этот файл — проверенная интерпретация для агента.
- При расхождении сначала сообщить о нём и обновить модель после review.
- Не считать `cancelled` как `done`; reopened — переход из `done` в нетерминальную группу.
