# Configuration reference

Use the user-level Codex configuration, never a project-committed token file.

```toml
[mcp_servers.mcp-atlassian]
command = "<path to uvx>"
args = ["mcp-atlassian==<verified-version>", "--transport", "stdio", "--read-only", "--toolsets", "<needed-toolsets>"]
env_vars = ["JIRA_URL", "JIRA_PERSONAL_TOKEN", "CONFLUENCE_URL", "CONFLUENCE_PERSONAL_TOKEN"]
startup_timeout_sec = 60
```

Use only the variables needed by the project. Do not print token values. Use the system trust store; do not disable TLS verification as a workaround.
