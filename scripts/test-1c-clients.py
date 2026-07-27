#!/usr/bin/env python3
"""The 1C client projections: what they own, what they must never touch.

The projections are rendered into files a person also edits, so most of these
checks are about what stays untouched rather than what gets written.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import one_c_clients as clients  # noqa: E402

CATALOG_TEMPLATE = ROOT / "templates/new-project/capabilities/1c/1c-mcp-catalog.template.json"
REGISTRY_FIELDS = (
    "project_id", "environment_id", "folder", "configuration", "platform_version",
    "compatibility_mode", "application_kind", "support_mode", "source_format",
    "edt_workspace", "edt_profile", "server_port", "is_production", "mcp_enabled", "owner",
)
failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def base_row(**overrides: str) -> str:
    values = {
        "project_id": "erp", "environment_id": "dev", "folder": "configurations/erp",
        "configuration": "ERP 2", "platform_version": "8.3.27.2025", "compatibility_mode": "8.3.27",
        "application_kind": "managed", "support_mode": "on-support", "source_format": "edt",
        "edt_workspace": "erp-ws", "edt_profile": "-", "server_port": "6003",
        "is_production": "false", "mcp_enabled": "true", "owner": "team",
    }
    values.update(overrides)
    return "\t".join(values[field] for field in REGISTRY_FIELDS)


def make_project(directory: Path, rows: tuple[str, ...] = (), catalog: dict | None = None) -> Path:
    (directory / "config").mkdir(parents=True, exist_ok=True)
    payload = catalog if catalog is not None else json.loads(CATALOG_TEMPLATE.read_bytes().decode("utf-8"))
    (directory / clients.CATALOG).write_bytes(
        (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    (directory / clients.REGISTRY).write_bytes(
        ("\n".join(["\t".join(REGISTRY_FIELDS), *rows]) + "\n").encode("utf-8"))
    return directory


def rendered(root: Path) -> tuple[dict, dict, str]:
    return (
        json.loads((root / clients.CLAUDE_SETTINGS).read_bytes().decode("utf-8")),
        json.loads((root / clients.MCP_CONFIG).read_bytes().decode("utf-8")),
        (root / clients.CODEX_CONFIG).read_bytes().decode("utf-8"),
    )


# --- the policy the table describes -----------------------------------------

with tempfile.TemporaryDirectory() as raw:
    project = make_project(Path(raw), (base_row(),))
    clients.apply(project)
    settings, mcp, codex = rendered(project)
    permissions = settings["permissions"]

    # Data MCP is denied: turning it on has to be a deliberate act outside the
    # conversation, so it must not be installed and must not be askable.
    note("mcp__onec-data" in permissions["deny"], "the data role must be denied")
    note(not any(name.startswith("onec-data") for name in mcp["mcpServers"]),
         "a denied role must not be installed")
    note("onec-data" not in codex or "не подключён" in codex, "Codex must not install the denied role")

    # A server that can both read and write gets the stricter class until it
    # says which tool is which; a reference server never needs a question.
    note("mcp__onec-edt" in permissions["ask"], "EDT must be ask while its tools are unknown")
    note("mcp__onec-toolkit-erp-dev" in permissions["ask"], "Toolkit must be ask")
    for role in ("syntax", "help", "ssl", "templates", "code-metadata", "graph-metadata", "code-check"):
        note(f"mcp__onec-{role}" in permissions["allow"], f"the {role} role must be allowed")

    # Only an endpoint that is actually known may be installed.
    note(list(mcp["mcpServers"]) == ["onec-toolkit-erp-dev"],
         f"only a resolvable endpoint may be installed: {list(mcp['mcpServers'])}")
    note("http://127.0.0.1:6003/mcp" == mcp["mcpServers"]["onec-toolkit-erp-dev"]["url"],
         "the toolkit URL must come from the registry port")

    before = rendered(project)
    changes = clients.apply(project)
    note(all(change["action"] in ("unchanged", "skip") for change in changes),
         f"a second render must change nothing: {[c for c in changes if c['action'] not in ('unchanged', 'skip')]}")
    note(before == rendered(project), "a second render must produce the same files")

# --- what belongs to the user -----------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    project = make_project(Path(raw), (base_row(),))
    (project / ".claude").mkdir()
    (project / clients.CLAUDE_SETTINGS).write_bytes(json.dumps({
        "model": "opus",
        "permissions": {"allow": ["Bash(git status)"], "deny": ["Read(./secrets/**)"]},
    }).encode("utf-8"))
    (project / clients.MCP_CONFIG).write_bytes(json.dumps({
        "mcpServers": {"github": {"type": "http", "url": "https://example"}},
    }).encode("utf-8"))
    (project / ".codex").mkdir()
    (project / clients.CODEX_CONFIG).write_bytes(b'model = "gpt-5"\n\n[mcp_servers.other]\nurl = "https://example"\n')

    clients.apply(project)
    settings, mcp, codex = rendered(project)
    note(settings["model"] == "opus", "an unrelated setting must survive")
    note("Bash(git status)" in settings["permissions"]["allow"], "a user rule must survive")
    note("Read(./secrets/**)" in settings["permissions"]["deny"], "a user deny rule must survive")
    note("github" in mcp["mcpServers"], "a third-party MCP server must survive")
    note('model = "gpt-5"' in codex and "[mcp_servers.other]" in codex, "user TOML must survive")

    # An owned rule that is no longer justified has to disappear, or a removed
    # base keeps its permission forever.
    settings["permissions"]["allow"].append("mcp__onec-toolkit-old-dev")
    (project / clients.CLAUDE_SETTINGS).write_bytes(json.dumps(settings).encode("utf-8"))
    clients.apply(project)
    settings, _, _ = rendered(project)
    note("mcp__onec-toolkit-old-dev" not in settings["permissions"]["allow"],
         "a stale owned rule must be dropped")

# --- registry drives what exists --------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    project = make_project(Path(raw), (base_row(), base_row(project_id="zup", server_port="6004")))
    clients.apply(project)
    _, mcp, _ = rendered(project)
    note(sorted(mcp["mcpServers"]) == ["onec-toolkit-erp-dev", "onec-toolkit-zup-dev"],
         f"one per-base server per base: {sorted(mcp['mcpServers'])}")

with tempfile.TemporaryDirectory() as raw:
    # A base that does not expose MCP has nothing to project.
    project = make_project(Path(raw), (base_row(mcp_enabled="false", server_port=""),))
    clients.apply(project)
    settings, mcp, _ = rendered(project)
    note(not mcp["mcpServers"], f"a base without MCP must install nothing: {mcp['mcpServers']}")
    note(not any(rule.startswith("mcp__onec-toolkit") for rule in settings["permissions"]["ask"]),
         "a base without MCP must not get a permission rule")

# --- tool precision when the catalog declares tools -------------------------

with tempfile.TemporaryDirectory() as raw:
    catalog = json.loads(CATALOG_TEMPLATE.read_bytes().decode("utf-8"))
    for server in catalog["servers"]:
        if server["role"] == "toolkit":
            server["tools"] = {"allow": ["read_object"], "ask": ["execute_code"]}
    project = make_project(Path(raw), (base_row(),), catalog)
    clients.apply(project)
    settings, _, _ = rendered(project)
    permissions = settings["permissions"]
    note("mcp__onec-toolkit-erp-dev__read_object" in permissions["allow"], "a declared read tool must be allowed")
    note("mcp__onec-toolkit-erp-dev__execute_code" in permissions["ask"], "a declared write tool must ask")
    # Anything the server did not classify keeps the area's class: a new
    # upstream tool must not arrive as allowed.
    note("mcp__onec-toolkit-erp-dev" in permissions["ask"], "the unclassified remainder must ask")

# --- bad input is a message, not a traceback --------------------------------

for name, payload in (
    ("no servers", {"schema_version": 1, "servers": []}),
    ("unknown role", {"schema_version": 1, "servers": [{"role": "shell", "provider_id": "x"}]}),
    ("server without a role", {"schema_version": 1, "servers": [{"provider_id": "x"}]}),
):
    with tempfile.TemporaryDirectory() as raw:
        project = make_project(Path(raw), (base_row(),), payload)
        try:
            clients.plan(project)
        except clients.ClientError:
            continue
        except Exception as error:  # noqa: BLE001
            failures.append(f"{name}: expected ClientError, got {type(error).__name__}")
            continue
        failures.append(f"{name}: expected ClientError, got a plan")

# --- the CLI reports before it writes ---------------------------------------

with tempfile.TemporaryDirectory() as raw:
    project = make_project(Path(raw), (base_row(),))
    report = subprocess.run(
        [sys.executable, str(SCRIPTS / "render-1c-clients.py"), "--root", str(project)],
        capture_output=True, text=True,
    )
    note(report.returncode == 1, "a pending change must be a non-zero exit")
    note(not (project / clients.MCP_CONFIG).exists(), "a report must not write anything")
    written = subprocess.run(
        [sys.executable, str(SCRIPTS / "render-1c-clients.py"), "--root", str(project), "--write"],
        capture_output=True, text=True,
    )
    note(written.returncode == 0, f"--write must succeed: {written.stderr[-200:]}")
    note((project / clients.MCP_CONFIG).is_file(), "--write must produce the projection")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} client projection check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All 1C client projection checks passed.")
