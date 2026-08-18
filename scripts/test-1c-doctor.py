#!/usr/bin/env python3
"""The diagnosis must stay inside its allowlist and must not carry a value out.

Both rules were text in a skill, and text is followed by whoever reads it. The
credential that started this came out of a session file during a broad walk of a
user profile, so "reads only what it declared" is checked by refusal, not by
inspection of the output.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("one_c_doctor", SCRIPTS / "one_c_doctor.py")
assert spec and spec.loader
doctor = importlib.util.module_from_spec(spec)
sys.modules["one_c_doctor"] = doctor
spec.loader.exec_module(doctor)

spec = importlib.util.spec_from_file_location("one_c_provider", SCRIPTS / "one_c_provider.py")
assert spec and spec.loader
provider = importlib.util.module_from_spec(spec)
sys.modules["one_c_provider"] = provider
spec.loader.exec_module(provider)

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

failures: list[str] = []


def note(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


# --- what may be opened ------------------------------------------------------

for relative in (".dev.env", "config/1c-projects.tsv", "configurations/launch/toolkit.launch"):
    note(doctor.allowed(relative), f"the allowlist must include {relative}")

for relative in (
    "../outside.md",                      # escaping the project
    "/etc/passwd",                        # absolute
    ".claude/state/session.json",         # state, where the credential came from
    ".codex/sessions/last.json",
    "logs/agent.log",
    "backups/dev.env",
    "README.md",                          # simply not declared
):
    note(not doctor.allowed(relative), f"the allowlist must refuse {relative}")

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    (root / ".claude/state").mkdir(parents=True)
    (root / ".claude/state/session.json").write_bytes(b'{"token": "ghp_secret"}')
    try:
        doctor.read(root, ".claude/state/session.json")
        failures.append("reading outside the allowlist must be refused, not merely avoided")
    except PermissionError:
        pass

    # --- a value never reaches the report ------------------------------------
    (root / ".dev.env").write_bytes(
        "\n".join([
            "# comment",
            "DEFAULT_PASSWORD=hunter2",
            "API_TOKEN=abcdef123456",
            "CONNECTION=Srvr=host;Ref=erp;",  # noscan - фикстура: сканер обязан её видеть, репозиторий - нет
            # Keys that carry a credential without carrying a marker word in the
            # value: these were printed whole while the check looked at the line.
            "DB_PWD=swordfish",
            "ONEC_CREDENTIAL=letmein",
            "BASE_LOGIN=admin",
            "EMPTY_SECRET=",
            "VERIFICATION_DEPTH=full",
            # Not a credential by any marker, and still a machine-specific path
            # the rest of the diagnosis takes care to hide.
            "EDT_WORKSPACE=D:\\wrk\\personspace",
        ]).encode("utf-8")
    )
    lines = doctor.settings(root)
    joined = "\n".join(lines)
    for value in ("hunter2", "abcdef123456", "host", "erp", "swordfish", "letmein", "admin"):
        note(value not in joined, f"the value '{value}' must never reach the report: {joined}")
    note(any(line.startswith("DEFAULT_PASSWORD") and doctor.MASK in line for line in lines),
         f"a set secret must be reported as set: {lines}")
    note(any("EMPTY_SECRET" in line and "не задан" in line for line in lines),
         f"an empty secret must be reported as unset: {lines}")
    # The row this feeds says values are not read — only the key and whether it
    # is set. That was true of keys a marker list recognised and false of every
    # other one, so a marker list that is always behind the names a project
    # invents was the only thing standing between the report and a user path.
    # Every value is now reported as set, including the ordinary ones.
    note(any(line == "VERIFICATION_DEPTH: задан" for line in lines),
         f"an ordinary value must not be printed either: {lines}")
    note("personspace" not in joined and "wrk" not in joined,
         f"a machine path must not reach the report: {joined}")
    # The decision is made on the key, so a key that names a credential is
    # masked even when nothing in its value looks like one.
    for key in ("DB_PWD", "ONEC_CREDENTIAL", "BASE_LOGIN"):
        note(any(line.startswith(key) and doctor.MASK in line for line in lines),
             f"{key} names a credential and must be reported as set, not printed: {lines}")
    note(not any(line.startswith("#") for line in lines), "comments are not settings")

    # --- every row says what it means and what to do -------------------------
    rows = doctor.report(root, names=("docker",))
    note(all(row.status in ("OK", "SKIP", "FAIL") for row in rows), f"unknown status: {rows}")
    note(all(row.action for row in rows), f"a row without a consequence is a number nobody acts on: {rows}")
    note(any(row.component == "реестр баз" for row in rows), "the registry must appear in the report")

    # A missing tool is a SKIP: the project is not broken by an absent optional.
    absent = doctor.tools(names=("no-such-tool",))
    note(absent[0].status == "SKIP", f"a missing tool must be SKIP, not FAIL: {absent}")

    rendered = doctor.render(rows)
    note("hunter2" not in rendered and "ghp_" not in rendered,
         "the rendered report must not carry a secret")

    # --- versions, patches and profiles --------------------------------------

    class Absent:
        status = "skipped"
        version = ""
        path = ""
        diagnostics = ["не найден ни в PATH, ни в известных местах установки"]

    edt = {row.component: row for row in doctor.edt_rows(root, discover=lambda name: Absent())}
    note("1C:EDT" in edt and "EDT-MCP" in edt and "патч Run without update" in edt,
         f"the report must name EDT, EDT-MCP and the conditional patch: {list(edt)}")
    note(edt["EDT-MCP"].status == "SKIP" and "EDT_MCP_VERSION" in edt["EDT-MCP"].detail,
         f"an unrecorded version must name the key to fill, not guess: {edt['EDT-MCP']}")
    note(all(row.action for row in edt.values()), f"every row must say what it costs: {edt}")

    (root / ".dev.env").write_bytes(b"EDT_MCP_VERSION=1.4.0\nEDT_RUN_WITHOUT_UPDATE=2026.1\n")
    edt = {row.component: row for row in doctor.edt_rows(root, discover=lambda name: Absent())}
    note(edt["EDT-MCP"].status == "OK" and "1.4.0" in edt["EDT-MCP"].detail,
         f"a recorded version must be reported: {edt['EDT-MCP']}")

# --- the diagnosis takes its keys from the catalog, not from a copy ----------

spec = importlib.util.spec_from_file_location("one_c_components", SCRIPTS / "one_c_components.py")
assert spec and spec.loader
catalog = importlib.util.module_from_spec(spec)
sys.modules["one_c_components"] = catalog
spec.loader.exec_module(catalog)

declared = {item.name: item.target for item in catalog.load(SCRIPTS.parent) if item.scheme == "env"}
for component, name in (("EDT-MCP", "EDT-MCP"),
                        ("патч Run without update", "Патч Run without update"),
                        ("плагин обычного приложения", "Плагин обычного приложения")):
    note(doctor.catalog_key(name, "СТАРЫЙ_КЛЮЧ") == declared.get(name),
         f"{component}: the diagnosis must read the key the catalog declares, not a copy")

# --- the registry is edited in a spreadsheet ---------------------------------
#
# Every other reader of these files opens them `utf-8-sig`; this one did not,
# so the BOM stayed on the first header cell. `project_id` became a key nobody
# looked up: every base in the report lost its name while the registry row of
# the same report said OK. A row with the wrong number of cells was dropped in
# silence, which reads as "this base is fine" rather than "not looked at".

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    (root / "config").mkdir()
    header = "project_id\tenvironment_id\tapplication_kind\tedt_profile\n"
    (root / "config/1c-projects.tsv").write_bytes(
        b"\xef\xbb\xbf" + (header + "erp\tdev\tordinary\terp-dev\n" + "broken\ttoo-few\n").encode("utf-8"))
    rows = doctor.registry_rows(root)
    note(rows and rows[0].get("project_id") == "erp",
         f"a BOM must not rename the first column: {rows[:1]}")
    note(any(row.get("status") == "unreadable" for row in rows),
         f"a row the reader cannot use must be named, not dropped: {rows}")


# --- the plugin and the launch profile belong to `ordinary` only -------------
#
# Three Toolkit builds exist and three profiles start them, all ordinary. A
# managed base has no build of ours, so no profile row is expected for it.

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    (root / "config").mkdir()
    header = "project_id\tenvironment_id\tapplication_kind\tedt_profile\n"
    (root / "config/1c-projects.tsv").write_bytes((header + "erp\tdev\tmanaged\t\n").encode("utf-8"))
    managed = doctor.ordinary_rows(root, doctor.registry_rows(root))
    note(all(row.status == "OK" for row in managed),
         f"for a managed base the absent plugin must not be a finding: {managed}")
    note(len(managed) == 1, f"a managed base has no Toolkit build of ours to profile: {managed}")

    (root / "config/1c-projects.tsv").write_bytes(
        (header + "erp\tdev\tordinary\terp-dev\n").encode("utf-8"))
    ordinary = {row.component: row for row in doctor.ordinary_rows(root, doctor.registry_rows(root))}
    note(ordinary["плагин обычного приложения"].status == "SKIP",
         f"for an ordinary base the plugin is required and missing: {ordinary}")
    note("профиль запуска erp/dev" in ordinary,
         f"an ordinary base must be checked for its launch profile: {list(ordinary)}")
    note(ordinary["профиль запуска erp/dev"].status == "SKIP",
         "a launch profile that is not there must be reported")

    (root / "configurations/launch").mkdir(parents=True, exist_ok=True)
    (root / "configurations/launch/erp-dev.launch").write_bytes(b"<launch/>")
    (root / ".dev.env").write_bytes(b"EDT_ORDINARY_PLUGIN=1.2.0\n")
    ordinary = {row.component: row for row in doctor.ordinary_rows(root, doctor.registry_rows(root))}
    note(ordinary["плагин обычного приложения"].status == "OK",
         f"a recorded plugin must be reported: {ordinary}")
    # Decision 1.16: the file being there says nothing about the client the base
    # will start as. A profile without the attribute starts the wrong one.
    note(ordinary["профиль запуска erp/dev"].status == "SKIP"
         and doctor.CLIENT_TYPE_ATTRIBUTE in ordinary["профиль запуска erp/dev"].detail,
         f"a profile without {doctor.CLIENT_TYPE_ATTRIBUTE} must not pass: {ordinary}")

    (root / "configurations/launch/erp-dev.launch").write_bytes(
        b'<launch><stringAttribute key="ATTR_CLIENT_TYPE" value="ordinary"/></launch>')
    ordinary = {row.component: row for row in doctor.ordinary_rows(root, doctor.registry_rows(root))}
    note(ordinary["профиль запуска erp/dev"].status == "OK",
         f"a complete profile must be found: {ordinary}")

    # --- naming a processor is not starting one (№253) -----------------------
    #
    # The check used to stop at "there is a /Execute", so a profile pointing at
    # a placeholder nobody substitutes reported that nothing was required. The
    # path is data, and data that names a file the project does not have is the
    # finding, not the reassurance.
    def profile(startup: str) -> dict:
        (root / "configurations/launch/erp-dev.launch").write_bytes(
            f'<launch><stringAttribute key="ATTR_CLIENT_TYPE" value="ordinary"/>'
            f'<stringAttribute key="ATTR_STARTUP_OPTION" value="{startup}"/></launch>'.encode("utf-8"))
        return {row.component: row for row in doctor.ordinary_rows(root, doctor.registry_rows(root))}

    placeholder = profile("/Execute &quot;&lt;PROJECT_ROOT&gt;/configurations/toolkit/T.epf&quot;")
    note(placeholder["профиль запуска erp/dev"].status == "SKIP",
         f"a profile starting a path that does not resolve must not pass: {placeholder}")

    missing = profile("/Execute &quot;configurations/toolkit/T.epf&quot;")
    note(missing["профиль запуска erp/dev"].status == "SKIP",
         f"a profile starting a file the project lacks must not pass: {missing}")

    (root / "configurations/toolkit").mkdir(parents=True, exist_ok=True)
    (root / "configurations/toolkit/T.epf").write_bytes(b"\x00binary\n")
    present = profile("/Execute &quot;configurations/toolkit/T.epf&quot;")
    note(present["профиль запуска erp/dev"].status == "OK",
         f"a profile starting a delivered processor must pass: {present}")
    note("configurations/toolkit/T.epf" in present["профиль запуска erp/dev"].detail,
         f"the report must name what gets started: {present}")

    # A machine-specific path is the defect the placeholder replaced, and it is
    # no more startable anywhere else than the placeholder is.
    absolute = profile("/Execute &quot;D:/build/toolkit/T.epf&quot;")
    note(absolute["профиль запуска erp/dev"].status == "SKIP",
         f"an absolute path belongs to one machine and must not pass: {absolute}")

# --- the shared proxy and channel collisions ---------------------------------
# Milestone W found 6003 already listened on by the platform and nothing
# reported it. Decision 1.8 was revised on 2026-08-18: one proxy serves every
# base on 6003, so an occupied port is now the working state and a free one is
# the finding. What the port range used to prevent - two bases answering the
# same commands - is now prevented by unique channels.

registry = [
    {"project_id": "erp", "environment_id": "dev", "toolkit_channel": "erp-dev", "mcp_enabled": "true"},
    {"project_id": "erp", "environment_id": "prod", "toolkit_channel": "", "mcp_enabled": "false"},
]
running = {row.component: row for row in doctor.channel_rows(registry, probe=lambda port: port == 6003)}
note(len(running) == 2, f"one proxy row and one channel row, and no row for a base without MCP: {running}")
note(running["прокси Toolkit :6003"].status == "OK",
     f"an occupied 6003 means the proxy is up: {running}")
note(running["канал erp-dev (erp/dev)"].status == "OK",
     f"a unique channel must pass: {running}")

stopped = doctor.channel_rows(registry, probe=lambda port: False)
note(stopped[0].status == "FAIL", f"a free 6003 means nothing will answer: {stopped}")

collided = doctor.channel_rows([
    {"project_id": "erp", "environment_id": "dev", "toolkit_channel": "shared", "mcp_enabled": "true"},
    {"project_id": "zup", "environment_id": "dev", "toolkit_channel": "shared", "mcp_enabled": "true"},
], probe=lambda port: True)
clash = [row for row in collided if row.status == "FAIL"]
note(len(clash) == 1, f"a repeated channel must be a finding: {collided}")
note("не в ту базу" in clash[0].action,
     f"the report must name the consequence: {clash[0]}")

# The probe binds rather than connects: a connection would answer about whoever
# listens anywhere, and the question is whether this machine can serve the base.
import socket  # noqa: E402

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as holder:
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    note(doctor.occupied(holder.getsockname()[1]), "a bound port must be seen as occupied")

# The listener that matters binds every interface — the 1C platform on 6003 does
# — and a probe that only asked 127.0.0.1 called such a port free.
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as holder:
    holder.bind(("", 0))
    holder.listen(1)
    note(doctor.occupied(holder.getsockname()[1]),
         "a port held on every interface must be seen as occupied")

# The check above cannot fail on POSIX: binding 0.0.0.0 already conflicts with a
# loopback probe there, so it would pass on the broken implementation too — the
# defect is specific to the Windows stack. What discriminates everywhere is
# which addresses the probe actually asks about, so that is asserted directly.
asked: list[str] = []


class RecordingSocket:
    def __init__(self, *arguments, **keywords) -> None:
        pass

    def __enter__(self) -> "RecordingSocket":
        return self

    def __exit__(self, *arguments) -> bool:
        return False

    def setsockopt(self, *arguments) -> None:
        pass

    def bind(self, address) -> None:
        asked.append(address[0])


original_socket = socket.socket
socket.socket = RecordingSocket
try:
    doctor.occupied(6003)
finally:
    socket.socket = original_socket
note("" in asked,
     f"the probe must ask about every interface, not only loopback: {asked}")

# --- the provider is reported, never started ---------------------------------

with tempfile.TemporaryDirectory() as raw:
    root = Path(raw)
    (root / "config").mkdir()
    (root / "config/1c-mcp-catalog.json").write_bytes(
        b'{"servers": [{"role": "syntax", "provider_id": "1c-syntax-checker-mcp", '
        b'"endpoint": "from-provider-manifest"}]}')
    # The environment of whoever runs the tests must not decide the answer.
    rows = doctor.provider_rows(root, discover=lambda project, servers: provider.discover(
        project, servers, environ={}, network=False))
    note(len(rows) == 1 and rows[0].status == "SKIP",
         f"without a manifest the provider is a SKIP with a reason: {rows}")
    note(rows[0].action, "the provider row must say what is unavailable")

    # A manifest that cannot be read is a row of the report. A traceback here
    # would break the tool exactly in the situation it exists to diagnose.
    (root / "broken-manifest.json").write_bytes(b"not json")
    (root / ".dev.env").write_bytes(
        f"MCP_PROVIDER_MANIFEST={root / 'broken-manifest.json'}\n".encode("utf-8"))
    rows = doctor.provider_rows(root)
    note(len(rows) == 1 and rows[0].status == "FAIL",
         f"an unreadable manifest must be a FAIL row, not an exception: {rows}")
    note(str(root) not in doctor.render(rows),
         f"the machine path must not reach the report: {doctor.render(rows)}")

    # And the path itself is masked the same way a value is.
    (root / ".dev.env").write_bytes(  # noscan - фикстура: путь обязан выглядеть машинным
        b"MCP_PROVIDER_MANIFEST=/home/somebody/secret-place/m.json\n")  # noscan - фикстура
    rows = doctor.provider_rows(root)
    note("secret-place" not in doctor.render(rows),
         f"a machine path from .dev.env must not reach the report: {doctor.render(rows)}")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} doctor check(s) failed.", file=sys.stderr)
    raise SystemExit(1)

print("Doctor checks passed.")
