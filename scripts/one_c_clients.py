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
server that does not declare its tools gets the strictest class of its area
rather than a plausible split between read and write. What the catalog may then
declare is bounded from above: it can narrow a class, never widen it.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import project_metadata  # noqa: E402

CATALOG = "config/1c-mcp-catalog.json"
REGISTRY = "config/1c-projects.tsv"
CLAUDE_SETTINGS = ".claude/settings.json"
MCP_CONFIG = ".mcp.json"
CODEX_CONFIG = ".codex/config.toml"
OWNED_PREFIX = "onec-"
BEGIN = "# new-project-rules:1c:begin"
END = "# new-project-rules:1c:end"
CLASSES = ("allow", "ask", "deny")
# The columns a projection reads; the registry may carry more.
REGISTRY_COLUMNS = ("project_id", "environment_id", "toolkit_channel", "mcp_enabled")
PROXY_PORT = project_metadata.ONE_C_TOOLKIT_PROXY_PORT
CHANNEL_RE = project_metadata.ONE_C_TOOLKIT_CHANNEL_RE
# Which projection belongs to which client, so a late-installed client can be
# activated without touching the one that already works (decision 1.11).
CLIENTS = {"claude": (CLAUDE_SETTINGS, MCP_CONFIG), "codex": (CODEX_CONFIG,)}

# Decision 1.17 with 1.31. Two different numbers, and conflating them is how a
# policy file becomes a way around the policy:
#
# * fallback — what the whole server gets while the catalog does not say which
#   tool is which. EDT and Toolkit mix reading and writing, so that is `ask`.
# * ceiling — the most a declared tool may be granted. The table allows Toolkit
#   and EDT reading, so their ceiling is `allow`; `data` may never be reached
#   at all, so its ceiling stays `deny` and a `tools` line cannot lift it.
ROLE_POLICY = {
    "syntax": ("allow", "allow"),
    "help": ("allow", "allow"),
    "ssl": ("allow", "allow"),
    "templates": ("allow", "allow"),
    "code-metadata": ("allow", "allow"),
    "graph-metadata": ("allow", "allow"),
    "code-check": ("allow", "allow"),
    "edt": ("ask", "allow"),
    "toolkit": ("ask", "allow"),
    "data": ("deny", "deny"),
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
        if server["role"] not in ROLE_POLICY:
            raise ClientError(f"{CATALOG} has an unknown role '{server['role']}'")
        tools = server.get("tools")
        if tools is not None:
            if not isinstance(tools, dict):
                raise ClientError(f"{CATALOG} role '{server['role']}': tools must be an object")
            for class_name, names in tools.items():
                if class_name not in CLASSES:
                    raise ClientError(f"{CATALOG} role '{server['role']}': unknown tool class '{class_name}'")
                # A bare string would be walked character by character and yield
                # rules that match nothing.
                if not isinstance(names, list) or not all(isinstance(name, str) and name for name in names):
                    raise ClientError(f"{CATALOG} role '{server['role']}': {class_name} must be a list of names")
    return servers


def read_utf8(path: Path, name: str) -> str:
    try:
        return path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ClientError(f"Cannot read {name}: {exc}") from exc


def read_registry(root: Path) -> list[dict[str, str]]:
    """Only the bases that expose MCP: the rest have nothing to project."""
    path = root / REGISTRY
    if not path.is_file():
        return []
    lines = read_utf8(path, REGISTRY).splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    missing = [column for column in REGISTRY_COLUMNS if column not in header]
    if missing:
        raise ClientError(f"{REGISTRY} has no column(s): {', '.join(missing)}")
    rows = []
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        values = line.split("\t")
        if len(values) != len(header):
            raise ClientError(f"{REGISTRY}:{number} has {len(values)} fields against {len(header)} in the header")
        row = dict(zip(header, values))
        if row["mcp_enabled"] == "true":
            channel = row["toolkit_channel"]
            # A base that says it exposes MCP but names no usable channel would
            # produce an endpoint that looks installed and times out on first
            # call: the proxy answers, nothing sits behind the channel.
            if not CHANNEL_RE.match(channel):
                raise ClientError(
                    f"{REGISTRY}:{number} exposes MCP with channel '{channel}'; "
                    "expected 1-64 characters of a-z, A-Z, 0-9, '_' or '-'."
                )
            rows.append(row)
    return rows


def server_name(server: dict, base: dict[str, str] | None = None) -> str:
    if base is None:
        return f"{OWNED_PREFIX}{server['role']}"
    return f"{OWNED_PREFIX}{server['role']}-{base['project_id']}-{base['environment_id']}"


def projected_servers(catalog: list[dict], registry: list[dict[str, str]],
                      resolved: dict[str, str] | None = None) -> list[dict]:
    """What each client should contain, and what it cannot contain yet.

    A per-base server exists once per infobase; a shared one exists once. An
    endpoint that only the provider manifest knows stays unresolved: a guessed
    URL would look installed and fail at the first call.

    `resolved` is what `one_c_provider` proved about an existing deployment —
    identity matched, health answered, tools declared. Only endpoints that
    passed that check may be registered; without it every provider endpoint
    stays unresolved, which is the state of a machine where the provider is not
    deployed.
    """
    resolved = resolved or {}
    projected: list[dict] = []
    taken: dict[str, str] = {}
    for server in catalog:
        bases = registry if server.get("scope") == "per-base" else [None]
        for base in bases:
            entry = {
                "name": server_name(server, base),
                "role": server["role"],
                "permission": ROLE_POLICY[server["role"]][0],
                "ceiling": ROLE_POLICY[server["role"]][1],
                "tools": server.get("tools") if isinstance(server.get("tools"), dict) else None,
                "url": "",
                "unresolved": "",
            }
            if server["role"] == "data":
                # Denied by policy: it must not be installed by a render.
                entry["unresolved"] = f"роль отключена решением 1.17 — {ROLE_REASONS['data']}"
            elif server.get("endpoint") == "proxy-channel" and base:
                entry["url"] = (
                    f"http://127.0.0.1:{PROXY_PORT}/mcp"
                    f"?channel={base['toolkit_channel']}"
                )
            elif resolved.get(server["provider_id"]):
                entry["url"] = resolved[server["provider_id"]]
            else:
                entry["unresolved"] = f"endpoint из provider manifest ({server['provider_id']})"
            # "erp-a"/"dev" and "erp"/"a-dev" are different bases with one name,
            # and the survivor would carry the other one's port — exactly the
            # "operation reached the wrong infobase" failure. Two catalog
            # servers of one role collide the same way and produce invalid TOML.
            identity = (f"{base['project_id']}/{base['environment_id']}" if base
                        else f"{CATALOG} role {server['role']}")
            if entry["name"] in taken:
                raise ClientError(
                    f"{taken[entry['name']]} and {identity} both project as "
                    f"'{entry['name']}'; one of them must be renamed."
                )
            taken[entry["name"]] = identity
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
        # A denied role gets one rule for the whole server: naming its tools
        # would only create ways to reach it.
        tools = None if entry["ceiling"] == "deny" else entry["tools"]
        if not tools:
            rules[entry["permission"]].append(f"mcp__{entry['name']}")
            continue
        for class_name in CLASSES:
            for tool in tools.get(class_name, ()):
                # The catalog may narrow a class, never widen it past the
                # ceiling: it is a file in the project, and a "tools" line must
                # not be able to lift a denied role into allow.
                rules[strictest(entry["ceiling"], class_name)].append(f"mcp__{entry['name']}__{tool}")
        # No server-wide rule here on purpose: Claude Code resolves deny, then
        # ask, then allow, so a server-wide "ask" would shadow every tool the
        # catalog allowed and the precision would never take effect. A tool the
        # catalog did not classify still asks — that is the client default.
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
        existing_rules = permissions.get(class_name, [])
        if not isinstance(existing_rules, list):
            raise ClientError(f"{CLAUDE_SETTINGS}: permissions.{class_name} must be a list")
        kept = [value for value in existing_rules if not owned_rule(value)]
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
        # Second barrier, at the writer. The provider already refuses an
        # endpoint that is not a plain http(s) URL, but this block is assembled
        # by concatenation: one quote and a newline in a value would close the
        # string and open a table naming any command as an MCP server. A writer
        # that cannot express a value must refuse it, not encode it wrong.
        if any(character in entry["url"] for character in ('"', "\\", "\r", "\n")):
            raise ClientError(
                f"{entry['name']}: endpoint contains a character that cannot appear in TOML: "
                f"{entry['url'][:60]}"
            )
        lines.append("")
        lines.append(f"[mcp_servers.{entry['name'].replace('-', '_')}]")
        lines.append(f'url = "{entry["url"]}"')
    lines.append(END)
    block = "\n".join(lines) + "\n"

    # Markers are matched as whole lines, and there must be exactly one pair in
    # the right order. A dangling marker — from an interrupted write, a hand
    # edit or a merge conflict — would otherwise make the next render swallow
    # everything between it and the marker of the block we just wrote.
    lines_in = existing.splitlines()
    starts = [number for number, line in enumerate(lines_in) if line.strip() == BEGIN]
    ends = [number for number, line in enumerate(lines_in) if line.strip() == END]
    if len(starts) > 1 or len(ends) > 1:
        raise ClientError(f"{CODEX_CONFIG} holds more than one 1c block; leave exactly one pair of markers")
    if bool(starts) != bool(ends):
        marker = BEGIN if starts else END
        raise ClientError(f"{CODEX_CONFIG}:{(starts or ends)[0] + 1} has '{marker}' without its pair")
    if starts and starts[0] > ends[0]:
        raise ClientError(f"{CODEX_CONFIG} has the 1c markers in the wrong order")
    if starts:
        kept = lines_in[:starts[0]] + block.splitlines() + lines_in[ends[0] + 1:]
        return "\n".join(kept) + "\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    return f"{existing}\n{block}" if existing else block


def canonical_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def plan(root: Path, client: str = "all",
         resolved: dict[str, str] | None = None) -> list[dict[str, str]]:
    """What each client file would become. Reading only; nothing is written."""
    if client != "all" and client not in CLIENTS:
        raise ClientError(f"Unknown client '{client}'; expected all, {', or '.join(sorted(CLIENTS))}")
    wanted = None if client == "all" else CLIENTS[client]
    projected = projected_servers(read_catalog(root), read_registry(root), resolved)
    changes: list[dict[str, str]] = []
    for name, content in (
        (CLAUDE_SETTINGS, canonical_json(render_claude_settings(read_json(root / CLAUDE_SETTINGS), projected))),
        (MCP_CONFIG, canonical_json(render_mcp_config(read_json(root / MCP_CONFIG), projected))),
        (CODEX_CONFIG, render_codex_config(
            read_utf8(root / CODEX_CONFIG, CODEX_CONFIG) if (root / CODEX_CONFIG).is_file() else "",
            projected,
        )),
    ):
        if wanted is not None and name not in wanted:
            continue
        path = root / name
        current = read_utf8(path, name) if path.is_file() else ""
        changes.append({
            "path": name,
            "action": "unchanged" if current == content else ("update" if current else "create"),
            "content": content,
        })
    for entry in projected:
        if entry["unresolved"]:
            changes.append({"path": entry["name"], "action": "skip", "content": entry["unresolved"]})
    return changes


def apply(root: Path, client: str = "all",
          resolved: dict[str, str] | None = None) -> list[dict[str, str]]:
    """Write in two phases: stage everything, then rename.

    Three files describe one policy. A failure halfway through would leave a
    project whose clients disagree about what is allowed, so the writes that
    can fail happen before any file is replaced.
    """
    changes = plan(root, client, resolved)
    pending = [change for change in changes if change["action"] in ("create", "update")]
    staged: list[tuple[Path, Path]] = []
    replaced: list[tuple[Path, bytes | None]] = []
    try:
        for change in pending:
            path = root / change["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            # A unique staging name: a second render running at the same time
            # must not delete this one's file, and a user file must not be hit.
            handle, staging_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".staged")
            os.close(handle)
            staging = Path(staging_name)
            staging.write_bytes(change["content"].encode("utf-8"))
            staged.append((staging, path))
        for staging, path in staged:
            # Renaming can fail too — on Windows a file held open by another
            # process — so the previous content is kept to undo what landed.
            replaced.append((path, path.read_bytes() if path.is_file() else None))
            staging.replace(path)
    except BaseException:
        for path, previous in reversed(replaced):
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous)
        raise
    finally:
        for staging, _ in staged:
            if staging.exists():
                staging.unlink()
    return changes
