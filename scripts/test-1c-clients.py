#!/usr/bin/env python3
"""The 1C client projections: what they own, what they must never touch.

The projections are rendered into files a person also edits, so most of these
checks are about what stays untouched rather than what gets written.
"""

from __future__ import annotations

import importlib.util
import json
import os
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
    "edt_workspace", "edt_profile", "toolkit_channel", "is_production", "mcp_enabled", "owner",
)
failures: list[str] = []

# The Toolkit range is one object, not two equal literals. Written out in both
# the validator and the renderer, widening it in one place produced a base the
# validator accepted and the renderer silently dropped.
import validate_project_support  # noqa: E402

if clients.CHANNEL_RE is not validate_project_support.ONE_C_TOOLKIT_CHANNEL_RE:
    failures.append(
        "the channel rule must come from validate_project_support, not be repeated: "
        f"{clients.CHANNEL_RE} vs {validate_project_support.ONE_C_TOOLKIT_CHANNEL_RE}"
    )
if clients.PROXY_PORT is not validate_project_support.ONE_C_TOOLKIT_PROXY_PORT:
    failures.append("the proxy port must come from validate_project_support, not be repeated")
validation_source = (ROOT / "scripts/one_c_validation.py").read_text(encoding="utf-8")
if "CHANNEL_RE = re.compile(" in validation_source:
    failures.append("one_c_validation.py must read the channel rule, not restate it")


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def base_row(**overrides: str) -> str:
    values = {
        "project_id": "erp", "environment_id": "dev", "folder": "configurations/erp",
        "configuration": "ERP 2", "platform_version": "8.3.27.2025", "compatibility_mode": "8.3.27",
        "application_kind": "managed", "support_mode": "on-support", "source_format": "edt",
        "edt_workspace": "erp-ws", "edt_profile": "-", "toolkit_channel": "erp-dev",
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
    note("http://127.0.0.1:6003/mcp?channel=erp-dev" == mcp["mcpServers"]["onec-toolkit-erp-dev"]["url"],
         "the toolkit URL must carry the channel from the registry")

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
    project = make_project(Path(raw), (base_row(), base_row(project_id="zup", toolkit_channel="zup-dev")))
    clients.apply(project)
    _, mcp, _ = rendered(project)
    note(sorted(mcp["mcpServers"]) == ["onec-toolkit-erp-dev", "onec-toolkit-zup-dev"],
         f"one per-base server per base: {sorted(mcp['mcpServers'])}")

with tempfile.TemporaryDirectory() as raw:
    # A base that does not expose MCP has nothing to project.
    project = make_project(Path(raw), (base_row(mcp_enabled="false", toolkit_channel=""),))
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
    # The precision has to take effect, not merely be present: Claude Code
    # resolves deny, then ask, then allow, so a server-wide "ask" alongside the
    # tools would shadow every tool the catalog allowed.
    note(not any(rule == "mcp__onec-toolkit-erp-dev" for rules in permissions.values() for rule in rules),
         "a server-wide rule must not shadow the declared tools")

# --- one policy, one name per base ------------------------------------------

with tempfile.TemporaryDirectory() as raw:
    # Two different identities that collapse into one server name: the survivor
    # would carry the other base's port.
    project = make_project(Path(raw), (
        base_row(project_id="erp-a", environment_id="dev"),
        base_row(project_id="erp", environment_id="a-dev", toolkit_channel="erp-a-dev"),
    ))
    try:
        clients.plan(project)
        failures.append("colliding base names must be refused")
    except clients.ClientError:
        pass

# --- a late client is activated on its own ----------------------------------

with tempfile.TemporaryDirectory() as raw:
    project = make_project(Path(raw), (base_row(),))
    clients.apply(project, "codex")
    note((project / clients.CODEX_CONFIG).is_file(), "--client codex must render the Codex projection")
    note(not (project / clients.MCP_CONFIG).exists(), "--client codex must not touch the Claude projection")
    clients.apply(project, "claude")
    note((project / clients.MCP_CONFIG).is_file(), "--client claude must render the Claude projection")
    try:
        clients.plan(project, "cursor")
        failures.append("an unknown client must be refused")
    except clients.ClientError:
        pass

# --- half-written projections are worse than none ---------------------------

def fails_on_last(function, calls: dict):
    """Let every call through but the last file's, which raises OSError."""
    def wrapper(*arguments, **keywords):
        calls["seen"] += 1
        if calls["seen"] == calls["fail_at"]:
            raise OSError("injected failure")
        return function(*arguments, **keywords)
    return wrapper


for phase, target in (("staging", "mkstemp"), ("rename", "replace")):
    with tempfile.TemporaryDirectory() as raw:
        project = make_project(Path(raw), (base_row(),))
        clients.apply(project)
        before = rendered(project)
        (project / clients.REGISTRY).write_bytes(
            ("\n".join(["\t".join(REGISTRY_FIELDS), base_row(toolkit_channel="erp-dev-alt")]) + "\n").encode("utf-8"))

        pending = [change for change in clients.plan(project) if change["action"] in ("create", "update")]
        note(len(pending) > 1, "the failure case needs more than one file to change")
        calls = {"seen": 0, "fail_at": len(pending)}
        if target == "mkstemp":
            original = clients.tempfile.mkstemp
            clients.tempfile.mkstemp = fails_on_last(original, calls)
        else:
            original = Path.replace
            Path.replace = fails_on_last(original, calls)
        try:
            clients.apply(project)
            failures.append(f"a failed {phase} must not report success")
        except OSError:
            pass
        finally:
            if target == "mkstemp":
                clients.tempfile.mkstemp = original
            else:
                Path.replace = original

        note(before == rendered(project),
             f"a failure during {phase} must leave every projection at its previous content")
        note(not list(project.glob("**/*.staged")), f"staging files must not survive a {phase} failure")

# --- a broken marker pair must not eat the user's file ----------------------

for case, body in (
    ("dangling begin", f'keep = 1\n{clients.BEGIN}\n'),
    ("dangling end", f'keep = 1\n{clients.END}\n'),
    ("markers reversed", f'{clients.END}\nkeep = 1\n{clients.BEGIN}\n'),
    ("two blocks", f'{clients.BEGIN}\n{clients.END}\n{clients.BEGIN}\n{clients.END}\n'),
):
    with tempfile.TemporaryDirectory() as raw:
        project = make_project(Path(raw), (base_row(),))
        (project / ".codex").mkdir()
        (project / clients.CODEX_CONFIG).write_bytes(body.encode("utf-8"))
        try:
            clients.plan(project)
            failures.append(f"{case}: a broken marker pair must be refused")
        except clients.ClientError:
            pass

with tempfile.TemporaryDirectory() as raw:
    # A marker that is part of a value is not a marker.
    project = make_project(Path(raw), (base_row(),))
    (project / ".codex").mkdir()
    (project / clients.CODEX_CONFIG).write_bytes(
        f'note = "{clients.BEGIN}"\nkeep = 1\n'.encode("utf-8"))
    clients.apply(project)
    codex = (project / clients.CODEX_CONFIG).read_bytes().decode("utf-8")
    note("keep = 1" in codex, "a marker inside a value must not swallow the next line")
    note(codex.count(clients.END) == 1, "exactly one block must be written")

# --- the catalog may narrow a class, never widen it -------------------------

with tempfile.TemporaryDirectory() as raw:
    catalog = json.loads(CATALOG_TEMPLATE.read_bytes().decode("utf-8"))
    for server in catalog["servers"]:
        if server["role"] in ("data", "edt"):
            server["tools"] = {"allow": ["read_all"]}
    project = make_project(Path(raw), (base_row(),), catalog)
    clients.apply(project)
    settings, mcp, _ = rendered(project)
    permissions = settings["permissions"]
    note("mcp__onec-data" in permissions["deny"], "a tools line must not lift a denied role")
    note(not any("onec-data" in rule for rule in permissions["allow"]), "a denied role must stay unreachable")
    note(not any("onec-data" in name for name in mcp["mcpServers"]), "a denied role must stay uninstalled")
    # EDT reading is allowed by the table, so a declared read tool may be allow.
    note("mcp__onec-edt__read_all" in permissions["allow"], "the table allows EDT reading")

# The ceiling is an invariant, not a property of today's roles: a class the
# catalog declares may be narrowed, never widened past what the table allows.
clamped = clients.permission_rules([{
    "name": "onec-example", "role": "toolkit", "permission": "ask", "ceiling": "ask",
    "tools": {"allow": ["read_object"]}, "url": "", "unresolved": "",
}])
note("mcp__onec-example__read_object" in clamped["ask"], "a declared class must not exceed the ceiling")
note(not clamped["allow"], f"nothing may be allowed above the ceiling: {clamped['allow']}")

with tempfile.TemporaryDirectory() as raw:
    # Two catalog servers of one role collide exactly like two bases do, and the
    # Codex block would hold the same table twice.
    catalog = json.loads(CATALOG_TEMPLATE.read_bytes().decode("utf-8"))
    catalog["servers"].append({"role": "help", "provider_id": "another-docs-mcp",
                               "scope": "provider-shared", "endpoint": "from-provider-manifest"})
    project = make_project(Path(raw), (base_row(),), catalog)
    try:
        clients.plan(project)
        failures.append("two catalog servers of one role must be refused")
    except clients.ClientError:
        pass

with tempfile.TemporaryDirectory() as raw:
    # A permission class the user left as a string would be walked character by
    # character and produce rules that match nothing.
    project = make_project(Path(raw), (base_row(),))
    (project / ".claude").mkdir()
    (project / clients.CLAUDE_SETTINGS).write_bytes(
        json.dumps({"permissions": {"allow": "Bash(ls)"}}).encode("utf-8"))
    try:
        clients.plan(project)
        failures.append("a permission class that is not a list must be refused")
    except clients.ClientError:
        pass

for name, payload in (
    ("tools is not an object", {"role": "toolkit", "provider_id": "x", "tools": ["read"]}),
    ("tool class is unknown", {"role": "toolkit", "provider_id": "x", "tools": {"maybe": ["read"]}}),
    ("tool list is a string", {"role": "toolkit", "provider_id": "x", "tools": {"allow": "read"}}),
):
    with tempfile.TemporaryDirectory() as raw:
        project = make_project(Path(raw), (base_row(),), {"schema_version": 1, "servers": [payload]})
        try:
            clients.plan(project)
            failures.append(f"{name}: expected ClientError, got a plan")
        except clients.ClientError:
            pass

# --- a hand-edited registry fails with a message ----------------------------

for name, content in (
    ("not UTF-8", "\t".join(REGISTRY_FIELDS).encode("utf-8") + "\n".encode("utf-8")
     + base_row(owner="комaнда").encode("cp1251")),
    ("missing column", b"project_id\tmcp_enabled\nerp\ttrue\n"),
    ("row longer than the header", ("\n".join(["\t".join(REGISTRY_FIELDS), base_row() + "\textra"]) + "\n").encode("utf-8")),
    ("exposed without a channel", ("\n".join(["\t".join(REGISTRY_FIELDS), base_row(toolkit_channel="")]) + "\n").encode("utf-8")),
    ("channel with forbidden characters", ("\n".join(["\t".join(REGISTRY_FIELDS), base_row(toolkit_channel="erp dev")]) + "\n").encode("utf-8")),
    # The identity becomes an MCP server name and a TOML table header. A quote
    # or a dot there produced a config.toml no client can parse — including the
    # user's own text outside our markers — and the renderer wrote it anyway,
    # because the rule lived in the validator and the validator is a separate
    # run (№248). Refusing an unrepresentable value is the writer's job.
    ("quote in project_id", ("\n".join(["\t".join(REGISTRY_FIELDS), base_row(project_id='erp"a')]) + "\n").encode("utf-8")),
    ("dot in project_id", ("\n".join(["\t".join(REGISTRY_FIELDS), base_row(project_id="erp.a")]) + "\n").encode("utf-8")),
    ("space in environment_id", ("\n".join(["\t".join(REGISTRY_FIELDS), base_row(environment_id="dev stand")]) + "\n").encode("utf-8")),
    ("upper case in project_id", ("\n".join(["\t".join(REGISTRY_FIELDS), base_row(project_id="ERP")]) + "\n").encode("utf-8")),
):
    with tempfile.TemporaryDirectory() as raw:
        project = make_project(Path(raw))
        (project / clients.REGISTRY).write_bytes(content)
        try:
            clients.plan(project)
            failures.append(f"{name}: expected ClientError, got a plan")
        except clients.ClientError:
            pass
        except Exception as error:  # noqa: BLE001
            failures.append(f"{name}: expected ClientError, got {type(error).__name__}")

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
        capture_output=True, text=True, encoding="utf-8",
    )
    note(report.returncode == 1, "a pending change must be a non-zero exit")
    note(not (project / clients.MCP_CONFIG).exists(), "a report must not write anything")
    # The report explains a SKIP in Russian, and the Windows console is not
    # UTF-8: the tool must not die on its own output.
    written = subprocess.run(
        [sys.executable, str(SCRIPTS / "render-1c-clients.py"), "--root", str(project), "--write"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )
    note(written.returncode == 0, f"--write must succeed: {written.stderr[-200:]}")
    note((project / clients.MCP_CONFIG).is_file(), "--write must produce the projection")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} client projection check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("All 1C client projection checks passed.")
