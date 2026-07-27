---
type: operations
status: active
owner: project
---

# Инструменты 1С

Что установлено на машине, какой версии и как это проверить. Заполняется
`doctor-1c`; вручную сюда пишут только то, что он ещё не умеет определять.

## Обязательные

| Компонент | Обнаруженная версия | Проверка |
|---|---|---|
| Git | | `git --version` |
| Python 3.9+ | | `python3 --version` |
| Платформа 1С | | ветка и сборка из списка баз |
| 1C:EDT | | `About` в EDT |
| EDT-MCP | | версия плагина |
| Docker Desktop | | `docker --version` |
| Внешний MCP provider | | health-check provider |
| Доступ к 1С:Напарнику | | health-check без вывода значения токена |

## По выбранным функциям

| Компонент | Нужен для | Обнаруженная версия |
|---|---|---|
| Плагин обычного приложения | `application_kind = ordinary` | |
| Патч `Run without update` | запуск без обновления конфигурации | |
| Node.js и `docx` | `md-to-docx` и CLI OpenSpec | |
| Pillow | `img-grid-analysis` | |
| `v8unpack` | offline unpack/repack CF/CFE/EPF | |
| YAxUnit | модульные тесты BSL | |
| BSL Language Server | проверка репозитория вне MCP | |

## Обработки Toolkit

SHA-256 каждой поставляемой обработки. Несовпадение блокирует весь Toolkit,
включая чтение: у обычного приложения только хеш отличает read-only сборку от
write-enabled.

| Обработка | Тип приложения | SHA-256 |
|---|---|---|

Секреты, токены, строки соединения и абсолютные машинные пути сюда не
записываются.
