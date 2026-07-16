# Atlassian MCP runbook

## Configuration

Configure the user-level Codex MCP server `mcp-atlassian`; do not commit tokens or machine paths.

Required environment variables are `JIRA_URL` and `JIRA_PERSONAL_TOKEN`; add `CONFLUENCE_URL` and `CONFLUENCE_PERSONAL_TOKEN` when Confluence is used. Keep `--read-only` by default.

## Verification

1. Confirm `uvx` and the configured `mcp-atlassian` version.
2. Confirm environment-variable presence without printing values.
3. Start a fresh Codex process, check MCP tools, then run read-only Jira and Confluence smoke tests.
4. Diagnose `401`, `403`, `404`, `409`, `429`, TLS, VPN and timeout before changing configuration.

## PAT

Create a Personal Access Token in the Jira or Confluence user profile, give it a clear name and expiry, copy it once to a password manager, and revoke/rotate it on compromise or expiry.
