---
name: setup-atlassian-mcp
description: Настраивает, проверяет и диагностирует доступ Codex к локальным Jira и Confluence Data Center через MCP-сервер mcp-atlassian. Использовать при первой настройке, ротации PAT, отсутствии MCP-инструментов, tool_count=0 или ошибках доступа; не использовать для прямых REST-вызовов.
---

# Настройка Atlassian MCP

1. Читать `docs/operations/ATLASSIAN_MCP_RUNBOOK.md`.
2. Проверить `uvx`, пользовательскую конфигурацию Codex и наличие переменных без вывода их значений.
3. Настроить `mcp-atlassian` c `--read-only` по умолчанию; не записывать токены, URL с credentials и абсолютные пути в Git.
4. Объяснить PAT: Jira/Confluence profile → Personal access tokens → Create token; выбрать назначение и expiry, сохранить значение один раз в password manager.
5. Открыть новый процесс Codex, проверить MCP-инструменты и выполнить read-only smoke test. При ошибке различать TLS/VPN, `401`, `403`, `404`, `429`, timeout и stale tool snapshot.

Не обходить MCP прямым REST, даже если MCP использует REST внутри.
