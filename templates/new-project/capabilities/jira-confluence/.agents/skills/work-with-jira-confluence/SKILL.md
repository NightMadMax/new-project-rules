---
name: work-with-jira-confluence
description: Анализирует Jira и ведёт связанную документацию Confluence через MCP-инструменты mcp-atlassian. Использовать для JQL/CQL, статусов, метрик, трассировки задач и документов, подготовки или безопасного обновления Confluence-страниц; не использовать для прямого REST.
---

# Работа с Jira и Confluence

1. Сначала читать `docs/jira/STATUS_MODEL.md`, `docs/jira/TRACEABILITY_MODEL.md`, `docs/confluence/DOCUMENT_MODEL.md` и `docs/analytics/QUERY_CATALOG.md`.
2. Выполнять Jira и Confluence операции только MCP-инструментами. Для аналитики дочитывать страницы и фиксировать JQL/CQL, время, timezone, scope и определение метрики.
3. Перед записью читать актуальное состояние. Показывать preview массовых изменений; сохранять labels, version и restrictions Confluence.
4. Связывать задачу и страницу двусторонне только после явного согласия пользователя. После записи перечитывать результат.

Разделять факты Atlassian и выводы агента; не считать недоступные по permissions данные отсутствующими.
