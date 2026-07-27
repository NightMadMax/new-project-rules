"""Client projections for capability 1c: one policy, three client files.

Claude Code, Codex and the MCP client each keep their own configuration, and
each is also edited by the person using them. So a projection has to do two
things at once: state the capability's policy exactly, and leave everything it
does not own untouched.

Ownership is by name, not by position: a server this capability installs is
called ``onec-…`` and a permission rule it owns matches ``mcp__onec-…``. Anything
else in the file belongs to the user and survives every render, which is what
makes re-running the renderer safe.

Two things are deliberately not invented here. An endpoint that the provider
manifest has to supply is reported as unresolved instead of guessed, and a
server that does not declare its tools gets the strictest class among its areas
rather than a plausible split between read and write.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CATALOG = "config/1c-mcp-catalog.json"
REGISTRY = "config/1c-projects.tsv"
CLAUDE_SETTINGS = ".claude/settings.json"
MCP_CONFIG = ".mcp.json"
CODEX_CONFIG = ".codex/config.toml"
OWNED_PREFIX = "onec-"
BEGIN = "# new-project-rules:1c:begin"
END = "# new-project-rules:1c:end"
CLASSES = ("allow", "ask", "deny")

# Decision 1.17. The class is a property of the area, and a server inherits the
# strictest class of the areas it covers unless it says which tool is which.
ROLE_CLASSES = {
    "syntax": "allow",
    "help": "allow",
    "ssl": "allow",
    "templates": "allow",
    "code-metadata": "allow",
    "graph-metadata": "allow",
    "code-check": "allow",
    "edt": "ask",
    "toolkit": "ask",
    "data": "deny",
}
ROLE_REASONS = {
    "edt": "чтение проектов allow, жизненный цикл ИБ и обновление конфигурации ask",
    "toolkit": "чтение allow, запись и execute_code ask",
    "data": "включение — отдельное действие после security review",
}


class ClientError(Exception):
    """The input a projection is built from is unusable."""


def strictest(*values: str) -> str:
    return max(values, key=CLASSES.index)


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClientError(f"Cannot read {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ClientError(f"{path.name} must hold a JSON object")
    return data


def read_catalog(root: Path) -> list[dict]:
    data = read_json(root / CATALOG)
    servers = data.get("servers")
    if not isinstance(servers, list) or not servers:
        raise ClientError(f"{CATALOG} declares no servers")
    for server in servers:
        if not isinstance(server, dict) or not server.get("role") or not server.get("provider_id"):
            raise ClientError(f"{CATALOG} has a server without a role or provider_id")
        if server["role"] not in ROLE_CLASSES:
            raise ClientError(f"{CATALOG} has an unknown role '{server['role']}'")
    return servers


def read_registry(root: Path) -> list[dict[str, str]]:
    """Only the bases that expose MCP: the rest have nothing to project."""
    path = root / REGISTRY
    if not path.is_file():
        return []
    lines = path.read_bytes().decode("utf-8-sig").splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = line.split("\t")
        if len(values) < len(header):
            raise ClientError(f"{REGISTRY} has a row that does not match the header")
        row = dict(zip(header, values))
        if row.get("mcp_enabled") == "true":
            rows.append(row)
    return rows


def server_name(server: dict, base: dict[str, str] | None = None) -> str:
    if base is None:
        return f"{OWNED_PREFIX}{server['role']}"
    return f"{OWNED_PREFIX}{server['role']}-{base['project_id']}-{base['environment_id']}"


def projected_servers(catalog: list[dict], registry: list[dict[str, str]]) -> list[dict]:
    """What each client should contain, and what it cannot contain yet.

    A per-base server exists once per infobase; a shared one exists once. An
    endpoint that only the provider manifest knows stays unresolved: a guessed
    URL would look installed and fail at the first call.
    """
    projected: list[dict] = []
    for server in catalog:
        bases = registry if server.get("scope") == "per-base" else [None]
        for base in bases:
            entry = {
                "name": server_name(server, base),
                "role": server["role"],
                "permission": ROLE_CLASSES[server["role"]],
                "tools": server.get("tools") if isinstance(server.get("tools"), dict) else None,
                "url": "",
                "unresolved": "",
            }
            if server["role"] == "data":
                # Denied by policy: it must not be installed by a render.
                entry["unresolved"] = "роль отключена решением 1.17"
            elif server.get("endpoint") == "local-port" and base:
                entry["url"] = f"http://127.0.0.1:{base['server_port']}/mcp"
            else:
                entry["unresolved"] = f"endpoint из provider manifest ({server['provider_id']})"
            projected.append(entry)
    return projected


def permission_rules(projected: list[dict]) -> dict[str, list[str]]:
    """Rules per class, in the form Claude Code matches on.

    Tool precision is used only where a server says which tool does what:
    read and write share a server in EDT and Toolkit, and inventing tool names
    would produce rules that match nothing.
    """
    rules: dict[str, list[str]] = {name: [] for name in CLASSES}
    for entry in projected:
        tools = entry["tools"]
        if not tools:
            rules[entry["permission"]].append(f"mcp__{entry['name']}")
            continue
        covered = "allow"
        for class_name in CLASSES:
            for tool in tools.get(class_name, ()):
                rules[class_name].append(f"mcp__{entry['name']}__{tool}")
                covered = strictest(covered, class_name)
        # Whatever the server did not classify keeps the area's own class, so a
        # new upstream tool cannot arrive silently as "allowed".
        rules[strictest(entry["permission"], covered)].append(f"mcp__{entry['name']}")
    return {name: sorted(set(values)) for name, values in rules.items()}


def owned_rule(value: object) -> bool:
    return isinstance(value, str) and value.startswith(f"mcp__{OWNED_PREFIX}")


def render_claude_settings(existing: dict, projected: list[dict]) -> dict:
    settings = json.loads(json.dumps(existing)) if existing else {}
    permissions = settings.get("permissions")
    if not isinstance(permissions, dict):
        permissions = {}
    rules = permission_rules(projected)
    for class_name in CLASSES:
        kept = [value for value in permissions.get(class_name, []) if not owned_rule(value)]
        merged = kept + [rule for rule in rules[class_name] if rule not in kept]
        if merged:
            permissions[class_name] = merged
        else:
            permissions.pop(class_name, None)
    settings["permissions"] = permissions
    return settings


def render_mcp_config(existing: dict, projected: list[dict]) -> dict:
    config = json.loads(json.dumps(existing)) if existing else {}
    servers = config.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    kept = {name: value for name, value in servers.items() if not name.startswith(OWNED_PREFIX)}
    for entry in projected:
        if entry["unresolved"]:
            continue
        kept[entry["name"]] = {"type": "http", "url": entry["url"]}
    config["mcpServers"] = dict(sorted(kept.items()))
    return config


def render_codex_config(existing: str, projected: list[dict]) -> str:
    """Codex keeps TOML, so the projection is a block, not a key.

    Everything outside the markers is the user's; the block is replaced whole,
    which is what makes a second render produce the same file.
    """
    lines = [BEGIN, "# Управляется capability 1c. Не редактировать внутри маркеров."]
    for entry in sorted(projected, key=lambda item: item["name"]):
        if entry["unresolved"]:
            lines.append(f"# {entry['name']}: не подключён — {entry['unresolved']}")
            continue
        lines.append("")
        lines.append(f"[mcp_servers.{entry['name'].replace('-', '_')}]")
        lines.append(f'url = "{entry["url"]}"')
    lines.append(END)
    block = "\n".join(lines) + "\n"

    if BEGIN in existing and END in existing:
        start = existing.index(BEGIN)
        finish = existing.index(END) + len(END) + 1
        return existing[:start] + block + existing[finish:]
    if existing and not existing.endswith("\n"):
        existing += "\n"
    return f"{existing}\n{block}" if existing else block


def canonical_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def plan(root: Path) -> list[dict[str, str]]:
    """What each client file would become. Reading only; nothing is written."""
    projected = projected_servers(read_catalog(root), read_registry(root))
    changes: list[dict[str, str]] = []
    for name, content in (
        (CLAUDE_SETTINGS, canonical_json(render_claude_settings(read_json(root / CLAUDE_SETTINGS), projected))),
        (MCP_CONFIG, canonical_json(render_mcp_config(read_json(root / MCP_CONFIG), projected))),
        (CODEX_CONFIG, render_codex_config(
            (root / CODEX_CONFIG).read_bytes().decode("utf-8") if (root / CODEX_CONFIG).is_file() else "",
            projected,
        )),
    ):
        path = root / name
        current = path.read_bytes().decode("utf-8") if path.is_file() else ""
        changes.append({
            "path": name,
            "action": "unchanged" if current == content else ("update" if current else "create"),
            "content": content,
        })
    for entry in projected:
        if entry["unresolved"]:
            changes.append({"path": entry["name"], "action": "skip", "content": entry["unresolved"]})
    return changes


def apply(root: Path) -> list[dict[str, str]]:
    changes = plan(root)
    for change in changes:
        if change["action"] in ("create", "update"):
            path = root / change["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(change["content"].encode("utf-8"))
    return changes
